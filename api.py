import json
import os
import subprocess
import yfinance as yf
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pipeline import rerun_subject_forced

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_DIR = os.path.dirname(__file__)
PREDICTIONS_FILE = os.path.join(_DIR, 'state', 'predictions.json')
SUBJECTS_FILE = os.path.join(_DIR, 'state', 'subjects.json')
SOURCES_LIB_FILE = os.path.join(_DIR, 'state', 'sources_library.json')


def _run_pipeline():
    subprocess.run(['python3', os.path.join(_DIR, 'pipeline.py')])


def load_predictions():
    with open(PREDICTIONS_FILE) as f:
        return json.load(f)


def save_predictions(data):
    with open(PREDICTIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@app.get("/api/predictions")
def get_predictions():
    predictions = load_predictions()
    today = datetime.now().strftime('%Y-%m-%d')
    for p in predictions:
        check = p.get('check_date', '')
        logged = p.get('date_logged', '')
        total_days = max((datetime.strptime(check, '%Y-%m-%d') - datetime.strptime(logged, '%Y-%m-%d')).days, 1)
        elapsed = (datetime.now() - datetime.strptime(logged, '%Y-%m-%d')).days
        p['days_remaining'] = max((datetime.strptime(check, '%Y-%m-%d') - datetime.now()).days, 0)
        p['progress_pct'] = min(round((elapsed / total_days) * 100), 100)
        p['overdue'] = today > check and p.get('outcome') is None
    return predictions


@app.get("/api/stats")
def get_stats():
    predictions = load_predictions()
    scored = [p for p in predictions if p.get('outcome') in ('correct', 'incorrect')]
    correct = [p for p in scored if p['outcome'] == 'correct']
    pending = [p for p in predictions if p.get('outcome') is None]
    return {
        "total": len(predictions),
        "scored": len(scored),
        "correct": len(correct),
        "incorrect": len(scored) - len(correct),
        "pending": len(pending),
        "accuracy": round(len(correct) / len(scored) * 100, 1) if scored else None
    }


@app.post("/api/predictions/{prediction_id}/score")
def score_prediction(prediction_id: str, body: dict):
    outcome = body.get('outcome')
    if outcome not in ('correct', 'incorrect', 'manual'):
        raise HTTPException(status_code=400, detail="Invalid outcome")
    predictions = load_predictions()
    for p in predictions:
        if p['id'] == prediction_id:
            ticker = p.get('ticker')
            current_price = None
            if ticker:
                try:
                    data = yf.Ticker(ticker)
                    current_price = round(data.fast_info.last_price, 2)
                except Exception:
                    pass
            p['outcome'] = outcome
            p['outcome_price'] = current_price
            p['outcome_date'] = datetime.now().strftime('%Y-%m-%d')
            save_predictions(predictions)
            return {"status": "ok", "prediction": p}
    raise HTTPException(status_code=404, detail="Prediction not found")


@app.delete("/api/predictions/{prediction_id}")
def discard_prediction(prediction_id: str):
    predictions = load_predictions()
    match = next((p for p in predictions if p['id'] == prediction_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Prediction not found")
    predictions = [p for p in predictions if p['id'] != prediction_id]
    save_predictions(predictions)
    with open(SUBJECTS_FILE) as f:
        subjects = json.load(f)
    subjects = [s for s in subjects if s['name'] != match['subject']]
    with open(SUBJECTS_FILE, 'w') as f:
        json.dump(subjects, f, indent=2)
    return {"status": "discarded"}


@app.get("/api/subjects")
def get_subjects():
    with open(SUBJECTS_FILE) as f:
        return json.load(f)


@app.put("/api/subjects")
async def update_subjects(request: Request):
    body = await request.json()
    with open(SUBJECTS_FILE, 'w') as f:
        json.dump(body, f, indent=2)
    return {"status": "ok"}


@app.post("/api/subjects")
def add_subject(body: dict, background_tasks: BackgroundTasks):
    name = body.get('name', '').strip()
    ticker = body.get('ticker', '').strip() or None
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    with open(SUBJECTS_FILE) as f:
        subjects = json.load(f)
    if any(s['name'].lower() == name.lower() for s in subjects):
        raise HTTPException(status_code=409, detail="Subject already exists")
    check_after_days = int(body.get('check_after_days', 1))
    timeline_mode = body.get('timeline_mode', 'auto')
    subjects.append({
        "name": name,
        "ticker": ticker,
        "category": "stock" if ticker else "general",
        "finnhub_ticker": ticker,
        "rss_feeds": [
            f"https://news.google.com/rss/search?q={name.replace(' ', '+')}+price+forecast&hl=en-US&gl=US&ceid=US:en"
        ],
        "check_after_days": check_after_days,
        "timeline_mode": timeline_mode
    })
    with open(SUBJECTS_FILE, 'w') as f:
        json.dump(subjects, f, indent=2)
    background_tasks.add_task(_run_pipeline)
    return {"status": "added", "running": True}


@app.get("/api/sources/library")
def get_sources_library():
    if not os.path.exists(SOURCES_LIB_FILE):
        return {}
    with open(SOURCES_LIB_FILE) as f:
        return json.load(f)


@app.post("/api/subjects/{name}/sources")
async def add_source(name: str, request: Request, background_tasks: BackgroundTasks):
    source = await request.json()
    if not source.get('id') or not source.get('url'):
        raise HTTPException(status_code=400, detail="id and url required")
    with open(SUBJECTS_FILE) as f:
        subjects = json.load(f)
    subj = next((s for s in subjects if s['name'] == name), None)
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    sources = subj.get('sources', subj.get('rss_feeds', []))
    if any((s.get('id') if isinstance(s, dict) else s) == source['id'] for s in sources):
        raise HTTPException(status_code=409, detail="Source already exists")
    if not isinstance(sources[0], dict) if sources else False:
        sources = [{'id': f"legacy_{i}", 'name': 'RSS', 'url': u, 'tier': 2, 'region': 'global', 'type': 'news'} for i, u in enumerate(sources)]
    sources.append(source)
    subj['sources'] = sources
    subj.pop('rss_feeds', None)
    with open(SUBJECTS_FILE, 'w') as f:
        json.dump(subjects, f, indent=2)
    background_tasks.add_task(rerun_subject_forced, name)
    return {"status": "added", "rerunning": True}


@app.delete("/api/subjects/{name}/sources/{source_id}")
def remove_source(name: str, source_id: str):
    with open(SUBJECTS_FILE) as f:
        subjects = json.load(f)
    subj = next((s for s in subjects if s['name'] == name), None)
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    sources = subj.get('sources', [])
    before = len(sources)
    sources = [s for s in sources if (s.get('id') if isinstance(s, dict) else s) != source_id]
    if len(sources) == before:
        raise HTTPException(status_code=404, detail="Source not found")
    subj['sources'] = sources
    with open(SUBJECTS_FILE, 'w') as f:
        json.dump(subjects, f, indent=2)
    return {"status": "removed"}


@app.post("/api/run")
def run_predictions(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_pipeline)
    return {"status": "running"}


@app.get("/api/sparkline/{ticker}")
def get_sparkline(ticker: str):
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="7d", interval="1d")
        prices = [round(float(p), 2) for p in hist['Close'].tolist()]
        return {"ticker": ticker, "prices": prices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/price/{ticker}")
def get_live_price(ticker: str):
    try:
        data = yf.Ticker(ticker)
        price = data.fast_info.last_price
        return {"ticker": ticker, "price": round(price, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
