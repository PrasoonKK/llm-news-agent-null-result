import os
import re
import time
import json
import hashlib
import statistics
import feedparser
import yfinance as yf
import requests
import certifi
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import quote

_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(_DIR, '.env'))

client = Groq(api_key=os.getenv('GROQ_API_KEY'))
FINNHUB_KEY = os.getenv('FINNHUB_API_KEY')

CACHE_FILE = os.path.join(_DIR, 'state', 'llm_cache.json')
PREDICTIONS_FILE = os.path.join(_DIR, 'state', 'predictions.json')
SUBJECTS_FILE = os.path.join(_DIR, 'state', 'subjects.json')
REPORTS_DIR = os.path.join(_DIR, 'reports')

# ── Frozen-study config ──────────────────────────────────────────────────────
# PIPELINE_VERSION is bumped by hand ONLY when a deliberate change is made. During the
# confirmatory run it must stay fixed; every prediction is stamped with it so the frozen
# set is filterable. pipeline_config_hash() auto-detects accidental prompt/model drift.
PIPELINE_VERSION = "1.0-frozen"
MODEL_LARGE = "openai/gpt-oss-120b"   # factor mapper, synthesizer, predictor, single-agent fallback
MODEL_SMALL = "openai/gpt-oss-20b"    # factor researchers
# Experiment arm: default ungated (Arm A) — the primary arm for directional data. Set EP_GATE=on
# to run the gated arm (Arm B). Only the `arm` field on records changes; config_hash is unaffected.
GATE_ENABLED = os.getenv('EP_GATE', 'off').lower() == 'on'


def pipeline_config_hash():
    """MD5 of the exact prompts + model IDs — proves the config didn't drift mid-study."""
    blob = "|".join([
        MODEL_LARGE, MODEL_SMALL,
        SIGNAL_PROMPT, FACTOR_MAPPER_PROMPT, FACTOR_RESEARCHER_PROMPT,
        SIGNAL_SYNTHESIZER_PROMPT, PREDICTOR_PROMPT,
    ])
    return hashlib.md5(blob.encode()).hexdigest()[:12]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

_vix_cache = None  # fetched once per pipeline run

_CALIBRATION_FILE = os.path.join(_DIR, 'state', 'calibration.json')

def get_calibration_context(ticker):
    """Returns pre-computed backtest calibration string for this ticker, or ''."""
    if not ticker:
        return ''
    try:
        if not os.path.exists(_CALIBRATION_FILE):
            return ''
        with open(_CALIBRATION_FILE) as f:
            cal = json.load(f)
        entry = cal.get(ticker, {})
        return entry.get('calibration_text', '')
    except Exception:
        return ''


def _append_prediction_entry(record):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    signals = '\n'.join(f'  - {s}' for s in record.get('signals', []))
    price = f"${record['baseline_price']}" if record.get('baseline_price') else 'N/A'
    entry = (
        f"## {record['subject']} — {record['direction'].upper()} | {record['date_logged']}\n\n"
        f"- **Confidence:** {record['confidence']}\n"
        f"- **Timeframe:** {record['timeframe']}\n"
        f"- **Baseline Price:** {price}\n"
        f"- **Event:** {record['event']}\n"
        f"- **Signals:**\n{signals}\n"
        f"- **Contra:** {record['contra']}\n"
        f"- **Reasoning:** {record['reasoning']}\n\n---\n\n"
    )
    with open(os.path.join(REPORTS_DIR, 'prediction_report.md'), 'a') as f:
        f.write(entry)


def load_subjects():
    with open(SUBJECTS_FILE) as f:
        return json.load(f)


SIGNAL_PROMPT = """You are a short-term signal extraction engine. Your job is to find forward-looking signals in news articles that indicate what might happen to {subject} within the next 1-14 days.

IMPORTANT: Focus exclusively on near-term catalysts — things happening THIS WEEK or NEXT WEEK. Ignore long-term trends, multi-month outlooks, or annual forecasts entirely. Only signals with impact within 2 weeks are relevant.

Look for: imminent earnings, upcoming Fed decisions, product launches this week, analyst price target changes, breaking supply/demand shifts, scheduled announcements, short-term momentum.

{timeline_hint}{earnings}{vix}{calibration}{context}{insider}{analyst}{feedback}
SIGNAL QUALITY: A valid directional signal must be one of: (a) a named, dated imminent event — earnings, product launch, scheduled announcement, or data release within 2 weeks; (b) a hard price/volume data point — momentum already moving 3%+ over 3 days, unusual volume spike, confirmed breakout; (c) a confirmed institutional action — insider buy/sell cluster, analyst rating change with a specific new price target. General sentiment, vague analyst optimism/pessimism, or news-cycle tone without a concrete trigger do NOT qualify as directional signals — treat them as background noise and lean neutral.

BIAS WARNING: News coverage is structurally negative — bad news gets more coverage than good. Do not mistake volume of coverage in either direction for a signal — it is not.

CRITICAL RULE: Only predict UP or DOWN when 2 or more QUALIFYING signals (see above) clearly point the same direction. If signals are mixed, thin, vague, or fail the quality bar — choose "neutral". A neutral prediction is scored as correct when there is no significant price move (within 2%). A wrong directional call is always worse than neutral. Do NOT call a direction to avoid neutral — neutral is often the right answer.

Source tiers: T1=official filings/wire (highest weight), T2=financial media, T3=social/Reddit (treat as sentiment only, not hard signal).

Articles (most recent first):
{posts}

Respond ONLY with a valid JSON object in this exact format:
{{
  "signals": [
    "signal 1 in one sentence — must be relevant within 2 weeks",
    "signal 2 in one sentence — must be relevant within 2 weeks",
    "signal 3 in one sentence — must be relevant within 2 weeks"
  ],
  "event": "The single most probable event within the next 1-14 days in one sentence",
  "direction": "up or down or shortage or surplus or neutral",
  "confidence": "low or medium or high",
  "confidence_reason": "Why this confidence level — how many sources agree, how specific and imminent the signals are",
  "timeframe": "MUST be short — prefer 1-3 days or 3-5 days. Only use 1-2 weeks if there is a specific scheduled event next week. Never exceed 2 weeks.",
  "contra": "The strongest reason the opposite direction could happen instead. If this is as strong as your thesis, choose neutral.",
  "reasoning": "2-3 sentences explaining the near-term prediction"
}}"""


FACTOR_MAPPER_PROMPT = """You are a financial research assistant. For the asset "{subject}", identify the 5 most important EXTERNAL factors that could drive short-term price movement within the next 1-2 weeks.

External factors = related companies, supply chain elements, macro events, sector dynamics, regulatory developments — NOT direct news about {subject} itself.

Return ONLY a JSON array of 5 Google News search queries (strings), no explanation:
["query 1", "query 2", "query 3", "query 4", "query 5"]"""


FACTOR_RESEARCHER_PROMPT = """Summarize the following news about "{factor}" as it relates to {subject}.

Articles:
{articles}

In 2-3 sentences, describe any concrete developments in the last 48 hours that could impact {subject}'s price within the next 2 weeks. Be specific — name events, dates, companies, numbers. If nothing relevant, respond exactly: No relevant developments."""


SIGNAL_SYNTHESIZER_PROMPT = """You are a signal quality filter for {subject}.

Score each piece of information below 1-3:
- Score 3 (QUALIFYING): Named imminent event with a date within 2 weeks (earnings, product launch, announcement), hard price/volume data (3%+ confirmed move, volume spike, breakout), confirmed institutional action (insider cluster buy/sell, analyst upgrade with specific new price target)
- Score 2 (WEAK): Analyst opinion without specific price target, general sector trend, indirectly relevant development
- Score 1 (NOISE): General sentiment, vague optimism/pessimism, news-cycle tone — EXCLUDE entirely

FACTOR RESEARCH SUMMARIES:
{factor_summaries}

DIRECT NEWS ARTICLES:
{direct_news}

Return ONLY a JSON array of signals scoring 2 or 3. Exclude all score-1 noise:
[
  {{"signal": "one sentence, specific and concrete", "score": 3, "direction_hint": "up or down or neutral"}},
  {{"signal": "one sentence, specific and concrete", "score": 2, "direction_hint": "up or down or neutral"}}
]"""


PREDICTOR_PROMPT = """You are a short-term market predictor for {subject}.

{vix}{earnings}{calibration}{context}{insider}{analyst}{feedback}
CRITICAL RULE: Only predict UP or DOWN when 2 or more Score-3 qualifying signals clearly point the same direction. Score-2 signals can support but cannot alone justify a directional call. If signals are mixed, thin, or only Score-2 — choose "neutral". Neutral is scored correct when price stays within ±2%. A wrong directional call is always worse than neutral.

BIAS WARNING: Do not mistake volume of news coverage for signal strength. Direction must be justified by qualifying signals only.

PRE-FILTERED SIGNALS (already scored for quality):
{signals}

Respond ONLY with a valid JSON object in this exact format:
{{
  "event": "The single most probable near-term event in one sentence",
  "direction": "up or down or neutral",
  "confidence": "low or medium or high",
  "confidence_reason": "Why this confidence level — how many Score-3 signals agree, how specific and imminent",
  "timeframe": "prefer 1-3 days or 3-5 days. Only use 1-2 weeks for a specific scheduled event. Never exceed 2 weeks.",
  "contra": "The strongest reason the opposite direction could happen instead. If as strong as thesis, choose neutral.",
  "reasoning": "2-3 sentences explaining the near-term prediction"
}}"""


def build_feedback_context(subject_name, all_predictions):
    scored = [p for p in all_predictions if p.get('outcome') in ('correct', 'incorrect')]
    if not scored:
        return ''

    lines = []

    # ── Global layer (always included) ───────────────────────────────────────
    total = len(scored)
    correct = sum(1 for p in scored if p['outcome'] == 'correct')
    global_acc = round(correct / total * 100)

    up_scored   = [p for p in scored if p.get('direction') == 'up']
    down_scored = [p for p in scored if p.get('direction') == 'down']
    up_acc   = round(sum(1 for p in up_scored   if p['outcome'] == 'correct') / len(up_scored)   * 100) if up_scored   else None
    down_acc = round(sum(1 for p in down_scored if p['outcome'] == 'correct') / len(down_scored) * 100) if down_scored else None

    hi_conf = [p for p in scored if p.get('confidence') == 'high']
    hi_acc  = round(sum(1 for p in hi_conf if p['outcome'] == 'correct') / len(hi_conf) * 100) if hi_conf else None

    lines.append(f"PAST PERFORMANCE — use this to calibrate your prediction:")
    lines.append(f"GLOBAL ({total} scored predictions, {global_acc}% accurate):")
    if up_acc is not None:
        lines.append(f"- UP predictions: {up_acc}% accurate ({len(up_scored)} calls)" +
                     (" — reliable" if up_acc >= 60 else " — weak, apply extra scrutiny"))
    if down_acc is not None:
        lines.append(f"- DOWN predictions: {down_acc}% accurate ({len(down_scored)} calls)" +
                     (" — reliable" if down_acc >= 60 else " — weak, apply extra scrutiny"))
    if hi_acc is not None and len(hi_conf) >= 2:
        lines.append(f"- High-confidence calls: {hi_acc}% accurate — " +
                     ("calibrated" if hi_acc >= 60 else "OVERCONFIDENT, downgrade your confidence this run"))

    # ── Per-subject layer (only if 2+ scored for this subject) ───────────────
    subj_scored = [p for p in scored if p['subject'] == subject_name]
    if len(subj_scored) >= 2:
        s_total   = len(subj_scored)
        s_correct = sum(1 for p in subj_scored if p['outcome'] == 'correct')
        s_acc     = round(s_correct / s_total * 100)

        s_up   = [p for p in subj_scored if p.get('direction') == 'up']
        s_down = [p for p in subj_scored if p.get('direction') == 'down']
        s_up_acc   = round(sum(1 for p in s_up   if p['outcome'] == 'correct') / len(s_up)   * 100) if s_up   else None
        s_down_acc = round(sum(1 for p in s_down if p['outcome'] == 'correct') / len(s_down) * 100) if s_down else None

        lines.append(f"\nSUBJECT-SPECIFIC — {subject_name} ({s_total} predictions, {s_acc}% accurate):")
        if s_up_acc is not None:
            lines.append(f"- UP calls: {s_up_acc}% accurate" +
                         (" — reliable" if s_up_acc >= 60 else " — historically weak for this subject"))
        if s_down_acc is not None:
            lines.append(f"- DOWN calls: {s_down_acc}% accurate" +
                         (" — reliable" if s_down_acc >= 60 else " — historically weak for this subject"))

    if not lines:
        return ''

    # ── Per-subject RAG layer (last 3 scored predictions with signal detail) ──
    if subj_scored:
        recent = subj_scored[-3:]
        lines.append(f"\nPAST {subject_name.upper()} PREDICTIONS (for calibration — note which signal types were right or wrong):")
        for p in recent:
            sigs = '; '.join(p.get('signals', [])) or 'N/A'
            chg = ''
            if p.get('baseline_price') and p.get('outcome_price'):
                pct = round(((p['outcome_price'] - p['baseline_price']) / p['baseline_price']) * 100, 1)
                chg = f" ({'+' if pct > 0 else ''}{pct}%)"
            lines.append(
                f"- {p['date_logged']}: Called {p['direction'].upper()} → {p['outcome'].upper()}{chg} | signals: {sigs}"
            )

    return "\n".join(lines) + "\n\n"


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE) as f:
        raw = json.load(f)
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    purged = {
        k: v for k, v in raw.items()
        if isinstance(v, dict) and v.get('date', '') >= cutoff
    }
    if len(purged) < len(raw):
        print(f"  Cache: purged {len(raw) - len(purged)} stale entries.")
        save_cache(purged)
    return purged


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


def load_predictions():
    if os.path.exists(PREDICTIONS_FILE):
        with open(PREDICTIONS_FILE) as f:
            return json.load(f)
    return []


def save_predictions(predictions):
    with open(PREDICTIONS_FILE, 'w') as f:
        json.dump(predictions, f, indent=2)


def fetch_rss(sources, cutoff_hours=168):
    posts = []
    reddit_ok = False
    has_reddit = any('reddit.com' in (s if isinstance(s, str) else s.get('url', '')) for s in sources)
    cutoff_ts = time.time() - (cutoff_hours * 3600)
    for src in sources:
        if isinstance(src, str):
            url, src_label = src, ''
        else:
            url = src['url']
            src_label = f"[{src.get('name', 'RSS')}][T{src.get('tier', 2)}] "
        is_reddit = 'reddit.com' in url
        try:
            r = requests.get(url, headers=HEADERS, verify=certifi.where(), timeout=10)
            if r.status_code != 200:
                print(f"  Warning: RSS returned {r.status_code} for {url[:60]}")
                if is_reddit:
                    time.sleep(4)
                continue
            feed = feedparser.parse(r.content)
            count_before = len(posts)
            for entry in feed.entries[:25]:
                title = entry.get('title', '').strip()
                summary = entry.get('summary', '').strip()[:250]
                if not title:
                    continue
                published = entry.get('published_parsed')
                if published:
                    entry_ts = time.mktime(published)
                    if entry_ts < cutoff_ts:
                        continue
                    date_label = f"[{datetime.fromtimestamp(entry_ts).strftime('%b %d')}] "
                else:
                    date_label = ''
                posts.append(f"- {src_label}{date_label}{title}. {summary}")
            if is_reddit and len(posts) > count_before:
                reddit_ok = True
        except Exception as e:
            print(f"  Warning: could not fetch {url[:60]}: {e}")
        if is_reddit:
            time.sleep(4)
    return posts, reddit_ok, has_reddit


def fetch_finnhub_news(ticker):
    if not ticker:
        return []
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={week_ago}&to={today}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        articles = r.json()
        posts = []
        for a in articles[:20]:
            headline = a.get('headline', '').strip()
            summary = a.get('summary', '').strip()[:200]
            ts = a.get('datetime', 0)
            date_label = f"[{datetime.fromtimestamp(ts).strftime('%b %d')}] " if ts else ''
            if headline:
                posts.append(f"- {date_label}{headline}. {summary}")
        return posts
    except Exception as e:
        print(f"  Warning: Finnhub fetch failed: {e}")
        return []


def get_price(ticker):
    if not ticker:
        return None
    try:
        price = yf.Ticker(ticker).fast_info.last_price
        return round(price, 2) if price else None
    except Exception:
        return None


def get_momentum_context(ticker):
    """Returns (context_str, hist_df, momentum_pct). hist_df reused for volume anomaly."""
    if not ticker:
        return '', None, None
    try:
        hist = yf.Ticker(ticker).history(period='10d')
        if len(hist) < 2:
            return '', hist, None
        current = round(float(hist['Close'].iloc[-1]), 2)
        lookback = hist['Close'].iloc[-4] if len(hist) >= 4 else hist['Close'].iloc[0]
        old = round(float(lookback), 2)
        change_pct = round((current - old) / old * 100, 1) if old else 0
        today = datetime.now().strftime('%Y-%m-%d')
        ctx = (
            f"CURRENT MARKET CONTEXT (as of {today}):\n"
            f"- {ticker} has moved {change_pct:+.1f}% over the last 3 days ({old} → {current})\n"
            f"- If this move is large (>3%), recent news may already be priced in — weight contrary signals higher.\n\n"
        )
        return ctx, hist, change_pct
    except Exception:
        return '', None, None


def get_volume_context(hist):
    """Detects unusual volume vs 10-day average. Pass hist from get_momentum_context."""
    if hist is None or 'Volume' not in hist.columns or len(hist) < 5:
        return ''
    try:
        avg_vol = float(hist['Volume'].iloc[:-1].mean())
        today_vol = float(hist['Volume'].iloc[-1])
        if avg_vol == 0:
            return ''
        ratio = today_vol / avg_vol
        if ratio > 2.0:
            return f"VOLUME ALERT: Today's trading volume is {ratio:.1f}x the 10-day average — unusual institutional activity detected.\n"
        return ''
    except Exception:
        return ''


def _get_earnings_date(ticker):
    """Returns the nearest earnings date within 14 days as a date object, or None."""
    if not ticker:
        return None
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None or (hasattr(cal, 'empty') and cal.empty):
            return None
        if hasattr(cal, 'columns') and 'Earnings Date' in cal.columns:
            dates = cal['Earnings Date'].dropna().tolist()
        elif hasattr(cal, 'index') and 'Earnings Date' in cal.index:
            raw = cal.loc['Earnings Date']
            dates = list(raw) if hasattr(raw, '__iter__') else [raw]
        else:
            return None
        for d in dates:
            try:
                d_date = d.date() if hasattr(d, 'date') else datetime.strptime(str(d)[:10], '%Y-%m-%d').date()
                days_away = (d_date - datetime.now().date()).days
                if 0 <= days_away <= 14:
                    return d_date
            except Exception:
                continue
        return None
    except Exception:
        return None


def get_earnings_context(ticker):
    """Returns a string if earnings are within 14 days, else ''."""
    d_date = _get_earnings_date(ticker)
    if not d_date:
        return ''
    days_away = (d_date - datetime.now().date()).days
    return (
        f"EARNINGS IN {days_away} DAY{'S' if days_away != 1 else ''} ({d_date}). "
        f"This is the dominant near-term catalyst — factor it heavily into your prediction.\n"
    )


_CAL_FILE = os.path.join(_DIR, 'state', 'calibration.json')

def has_hard_catalyst(ticker, earnings, insider, momentum_pct):
    """Deterministic gate: a directional call is only permitted when one of these fires.
    Returns (bool, reason)."""
    if earnings:
        return True, 'earnings'
    if insider:
        return True, 'insider'
    if ticker and momentum_pct is not None:
        try:
            with open(_CAL_FILE) as f:
                cal = json.load(f).get(ticker)
            if cal:
                if momentum_pct > 2.0 and (cal.get('momentum_bull_rate') or 0) >= 0.55:
                    return True, 'momentum'
                if momentum_pct < -2.0 and (cal.get('momentum_bear_rate') or 0) >= 0.55:
                    return True, 'momentum'
        except Exception:
            pass
    return False, None


def get_vix_context():
    """Fetched once per pipeline run (module-level cache)."""
    global _vix_cache
    if _vix_cache is not None:
        return _vix_cache
    try:
        hist = yf.Ticker('^VIX').history(period='30d')['Close']
        if len(hist) < 5:
            _vix_cache = ''
            return ''
        current = round(float(hist.iloc[-1]), 1)
        avg = round(float(hist.mean()), 1)
        if current > avg:
            regime = f'elevated ({current} vs {avg} avg) — larger moves expected, higher uncertainty'
        else:
            regime = f'calm ({current} vs {avg} avg) — signals more reliable, smaller moves expected'
        _vix_cache = f"Market VIX: {regime}.\n"
        return _vix_cache
    except Exception:
        _vix_cache = ''
        return ''


_crypto_fg_cache = None

def get_crypto_fg_context():
    """Crypto Fear & Greed from alternative.me. Fetched once per run."""
    global _crypto_fg_cache
    if _crypto_fg_cache is not None:
        return _crypto_fg_cache
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        d = r.json()["data"][0]
        score = int(d["value"])
        label = d["value_classification"]
        if score <= 25:
            interp = "extreme panic selling — strong bearish sentiment"
        elif score <= 45:
            interp = "fear — cautious sentiment"
        elif score <= 55:
            interp = "neutral sentiment"
        elif score <= 75:
            interp = "greed — bullish sentiment, potential continuation"
        else:
            interp = "extreme greed — overheated, correction risk"
        _crypto_fg_cache = f"Crypto Fear & Greed: {score}/100 ({label}) — {interp}.\n"
        return _crypto_fg_cache
    except Exception:
        _crypto_fg_cache = ''
        return ''


def get_insider_context(ticker):
    """Checks Finnhub insider transactions (free tier) for recent cluster buys/sells."""
    if not ticker or not FINNHUB_KEY:
        return ''
    try:
        url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&limit=20&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=8)
        data = r.json().get('data', [])
        cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        recent = [x for x in data if x.get('transactionDate', '') >= cutoff]
        buys  = [x for x in recent if x.get('transactionCode') == 'P']
        sells = [x for x in recent if x.get('transactionCode') == 'S']
        if len(buys) >= 2:
            return f"INSIDER SIGNAL: {len(buys)} insider purchase(s) filed in the last 7 days — bullish signal.\n"
        if len(sells) >= 3:
            return f"INSIDER SIGNAL: {len(sells)} insider sale(s) filed in the last 7 days — bearish signal.\n"
        return ''
    except Exception:
        return ''


def get_analyst_context(ticker):
    """Checks Finnhub analyst consensus (free tier)."""
    if not ticker or not FINNHUB_KEY:
        return ''
    try:
        url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={FINNHUB_KEY}"
        recs = requests.get(url, timeout=8).json()
        if not recs:
            return ''
        latest = recs[0]
        total = latest.get('buy', 0) + latest.get('hold', 0) + latest.get('sell', 0)
        if total == 0:
            return ''
        buy_pct = round(latest['buy'] / total * 100)
        return (
            f"Analyst consensus: {buy_pct}% buy "
            f"({latest['buy']} buy / {latest['hold']} hold / {latest['sell']} sell).\n"
        )
    except Exception:
        return ''


def call_groq(prompt, cache):
    key = hashlib.md5(prompt.encode()).hexdigest()
    if key in cache:
        print("  (using cached LLM response)")
        return cache[key]['response']

    response = client.chat.completions.create(
        model=MODEL_LARGE,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2200,  # gpt-oss reasoning tokens share this budget — 1200 was truncating output to empty
        temperature=0.3,
        reasoning_effort="low",
    )
    result = response.choices[0].message.content.strip()
    if result:  # don't cache truncated/empty responses — they'd poison every future call with this prompt
        cache[key] = {'response': result, 'date': datetime.now().strftime('%Y-%m-%d')}
        save_cache(cache)
    return result


def call_groq_small(prompt, cache):
    key = hashlib.md5(("8b:" + prompt).encode()).hexdigest()
    if key in cache:
        return cache[key]['response']
    response = client.chat.completions.create(
        model=MODEL_SMALL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.3,
        reasoning_effort="low",
    )
    result = response.choices[0].message.content.strip()
    if result:
        cache[key] = {'response': result, 'date': datetime.now().strftime('%Y-%m-%d')}
        save_cache(cache)
    return result


def build_factor_rss_url(query):
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"


def run_factor_mapper(subject_name, cache):
    prompt = FACTOR_MAPPER_PROMPT.format(subject=subject_name)
    raw = call_groq(prompt, cache)
    try:
        start = raw.find('[')
        end = raw.rfind(']') + 1
        queries = json.loads(raw[start:end])
        return queries[:5] if isinstance(queries, list) else []
    except Exception:
        print(f"  Factor mapper parse failed: {raw[:100]}")
        return []


def run_factor_researcher(subject_name, factor_query, cache):
    posts, _, _ = fetch_rss([build_factor_rss_url(factor_query)], cutoff_hours=48)
    if not posts:
        return f"No relevant developments. (no articles found for: {factor_query})"
    articles_text = "\n".join(posts[:8])
    prompt = FACTOR_RESEARCHER_PROMPT.format(
        factor=factor_query,
        subject=subject_name,
        articles=articles_text,
    )
    return call_groq_small(prompt, cache)


def run_signal_synthesizer(subject_name, factor_summaries, direct_posts, cache):
    factors_text = "\n\n".join(
        f"Factor: {q}\n{s}" for q, s in factor_summaries
        if not s.startswith("No relevant")
    ) or "No external factor developments found."
    direct_text = "\n".join(direct_posts[:20]) or "No direct news articles."
    prompt = SIGNAL_SYNTHESIZER_PROMPT.format(
        subject=subject_name,
        factor_summaries=factors_text,
        direct_news=direct_text,
    )
    raw = call_groq(prompt, cache)
    try:
        start = raw.find('[')
        end = raw.rfind(']') + 1
        signals = json.loads(raw[start:end])
        return signals if isinstance(signals, list) else []
    except Exception:
        print(f"  Synthesizer parse failed: {raw[:100]}")
        return []


def parse_timeframe_days(timeframe):
    t = timeframe.lower()
    nums = list(map(int, re.findall(r'\d+', t)))
    if not nums:
        return 0
    n = max(nums)
    if 'month' in t:  return n * 30
    if 'week'  in t:  return n * 7
    if 'day'   in t:  return n
    return 0


def run_subject(subject, cache, all_predictions=None):
    print(f"\n{'='*50}")
    print(f"Subject: {subject['name']}")
    print(f"{'='*50}")

    tier = subject.get('tier', 'short')
    tier_cap = 14  # ponytail: prompt already enforces 2-week max; hard 5d cap was too tight
    cutoff_hours = 48 if tier == 'short' else 168

    # ── Fetch structured signals (non-news) ──────────────────────────────────
    ticker = subject.get('ticker')

    calibration = get_calibration_context(ticker)
    if calibration:
        print("  Injecting historical calibration.")

    momentum_ctx, hist, momentum_pct = get_momentum_context(ticker)
    volume_ctx = get_volume_context(hist)
    context = momentum_ctx + volume_ctx

    earnings = get_earnings_context(ticker)
    if earnings:
        print(f"  {earnings.strip()}")

    vix = get_vix_context()
    if subject.get('category') == 'crypto':
        vix += get_crypto_fg_context()

    finnhub_ticker = subject.get('finnhub_ticker')
    insider = get_insider_context(finnhub_ticker)
    analyst = get_analyst_context(finnhub_ticker)
    if insider:
        print(f"  {insider.strip()}")

    # ── Fetch news ────────────────────────────────────────────────────────────
    posts = []

    if finnhub_ticker:
        print("  Fetching Finnhub news...")
        finnhub_posts = fetch_finnhub_news(finnhub_ticker)
        posts.extend(finnhub_posts)
        print(f"  Got {len(finnhub_posts)} articles from Finnhub.")

    print(f"  Fetching RSS feeds (last {cutoff_hours}h)...")
    rss_posts, reddit_ok, has_reddit = fetch_rss(subject.get('sources', subject.get('rss_feeds', [])), cutoff_hours=cutoff_hours)
    posts.extend(rss_posts)
    print(f"  Got {len(rss_posts)} fresh articles from RSS.")
    if has_reddit and not reddit_ok:
        print(f"  Reddit unavailable (429) — proceeding without it.")

    if not posts:
        print("  No articles found, skipping.")
        return None

    feedback = build_feedback_context(subject['name'], all_predictions or [])
    if feedback:
        print("  Injecting feedback context.")

    custom = subject.get('timeline_mode') == 'custom'
    days = subject['check_after_days']
    if custom:
        label = f"{days} day{'s' if days > 1 else ''}"
        timeline_hint = (
            f"IMPORTANT — USER-SPECIFIED TIMELINE: {label}. "
            f"Focus ONLY on signals with impact within the next {label}. "
            f"Prioritise breaking news, imminent catalysts, and short-term momentum. "
            f"Ignore signals about trends or events playing out beyond {label}. "
            f"Your timeframe field in the response must reflect this {label} window.\n\n"
        )
        print(f"  Custom timeline: {label} — injecting into prompt.")
    else:
        timeline_hint = ''

    prediction = None

    # ── Multi-agent pipeline ──────────────────────────────────────────────────
    try:
        print(f"  [Multi-agent] Step 1/4: Factor Mapper...")
        factor_queries = run_factor_mapper(subject['name'], cache)
        if factor_queries:
            print(f"  [Multi-agent] Step 2/4: Factor Researchers (x{len(factor_queries)})...")
            factor_summaries = [(q, run_factor_researcher(subject['name'], q, cache)) for q in factor_queries]
            print(f"  [Multi-agent] Step 3/4: Signal Synthesizer...")
            scored_signals = run_signal_synthesizer(subject['name'], factor_summaries, posts, cache)

            # Format signals for predictor
            if scored_signals:
                sig_lines = "\n".join(
                    f"- [Score {s.get('score',2)}] {s.get('signal','')} (hint: {s.get('direction_hint','?')})"
                    for s in scored_signals
                )
            else:
                sig_lines = "No qualifying signals found after filtering."

            print(f"  [Multi-agent] Step 4/4: Predictor ({len(scored_signals)} signals)...")
            pred_prompt = PREDICTOR_PROMPT.format(
                subject=subject['name'],
                vix=vix,
                earnings=earnings,
                calibration=calibration,
                context=context,
                insider=insider,
                analyst=analyst,
                feedback=feedback,
                signals=sig_lines,
            )
            raw = call_groq(pred_prompt, cache)
            start = raw.find('{')
            end = raw.rfind('}') + 1
            prediction = json.loads(raw[start:end])
            # Attach raw signal sentences as the signals list (from scored signals)
            if 'signals' not in prediction:
                prediction['signals'] = [s.get('signal', '') for s in scored_signals if s.get('score', 1) >= 2]
            print("  [Multi-agent] Pipeline complete.")
    except Exception as e:
        print(f"  [Multi-agent] Failed ({e}) — falling back to single-agent.")
        prediction = None

    # ── Single-agent fallback ─────────────────────────────────────────────────
    if prediction is None:
        print(f"  Extracting signals via single-agent Groq...")
        posts_text = "\n".join(posts[:30])
        prompt = SIGNAL_PROMPT.format(
            subject=subject['name'],
            timeline_hint=timeline_hint,
            earnings=earnings,
            vix=vix,
            calibration=calibration,
            context=context,
            insider=insider,
            analyst=analyst,
            feedback=feedback,
            posts=posts_text,
        )
        raw = call_groq(prompt, cache)
        try:
            start = raw.find('{')
            end = raw.rfind('}') + 1
            prediction = json.loads(raw[start:end])
        except Exception:
            print("  Warning: could not parse LLM response as JSON")
            print("  Raw response:", raw[:300])
            return None

    # ── Catalyst gate (Arm B only): permit UP/DOWN only when a deterministic catalyst backs it ──
    if GATE_ENABLED and prediction.get('direction') in ('up', 'down'):
        catalyst_ok, catalyst_reason = has_hard_catalyst(ticker, earnings, insider, momentum_pct)
        if not catalyst_ok:
            print(f"  Catalyst gate: no hard catalyst for {prediction['direction'].upper()} call — forcing NEUTRAL.")
            prediction['direction'] = 'neutral'
            prediction['contra'] = prediction.get('reasoning', prediction.get('contra', ''))
            prediction['reasoning'] = (
                "Downgraded to neutral by the catalyst gate — no earnings, insider cluster, "
                "or backtest-confirmed momentum pattern supported a directional call. " + prediction.get('reasoning', '')
            )
        else:
            print(f"  Catalyst gate: {prediction['direction'].upper()} call backed by {catalyst_reason}.")

    price = get_price(ticker)
    # Don't log an uncollectable record: a ticker'd subject with no baseline price can never be scored
    # and would permanently block that subject from re-predicting. Skip and retry next run instead.
    if ticker and price is None:
        print(f"  No baseline price for {ticker} (fetch failed) — skipping, will retry next run.")
        return None

    if custom:
        check_after_days = subject['check_after_days']
    else:
        model_days = parse_timeframe_days(prediction.get('timeframe', ''))
        check_after_days = min(model_days or subject['check_after_days'], tier_cap)

    # If earnings fall after the default check date but within 14 days, push check date to day after earnings
    earnings_date = _get_earnings_date(ticker)
    default_check = datetime.now().date() + timedelta(days=check_after_days)
    if earnings_date and earnings_date > default_check:
        check_date = (earnings_date + timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"  Earnings on {earnings_date} — check date pushed to {check_date}")
    else:
        check_date = default_check.strftime('%Y-%m-%d')

    # Daily-return volatility at prediction time — powers the volatility-scaled neutral band (robustness).
    neutral_sigma = None
    try:
        if hist is not None and len(hist) >= 4:
            # drop NaNs — yfinance's latest bar is often an incomplete candle
            closes = [float(c) for c in hist['Close'] if c == c]
            rets = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes)) if closes[i-1]]
            if len(rets) >= 2:
                neutral_sigma = round(statistics.stdev(rets), 3)
    except Exception:
        pass

    record = {
        "id": hashlib.md5(f"{subject['name']}{datetime.now().date()}".encode()).hexdigest()[:8],
        "subject": subject['name'],
        "category": subject['category'],
        "ticker": ticker,
        "tier": tier,
        "pipeline_version": PIPELINE_VERSION,
        "config_hash": pipeline_config_hash(),
        "arm": "gated" if GATE_ENABLED else "ungated",
        "neutral_sigma": neutral_sigma,
        "date_logged": datetime.now().strftime('%Y-%m-%d'),
        "check_date": check_date,
        "baseline_price": price,
        "signals": prediction.get('signals', []),
        "event": prediction.get('event', ''),
        "direction": prediction.get('direction', ''),
        "confidence": prediction.get('confidence', ''),
        "confidence_reason": prediction.get('confidence_reason', ''),
        "timeframe": prediction.get('timeframe', ''),
        "contra": prediction.get('contra', ''),
        "reasoning": prediction.get('reasoning', ''),
        "outcome": None,
        "outcome_price": None,
        "outcome_date": None
    }

    print(f"\n  Event:      {record['event']}")
    print(f"  Direction:  {record['direction'].upper()}")
    print(f"  Confidence: {record['confidence'].upper()} — {record['confidence_reason']}")
    print(f"  Timeframe:  {record['timeframe']}")
    print(f"  Contra:     {record['contra']}")
    print(f"  Baseline:   {'$' + str(price) if price else 'N/A (no ticker)'}")
    print(f"  Check on:   {check_date} (tier: {tier}, cap: {tier_cap}d)")
    print(f"\n  Signals found:")
    for s in record['signals']:
        print(f"    • {s}")
    print(f"\n  Reasoning: {record['reasoning']}")

    return record


def main(limit=None):
    """limit: process at most this many eligible subjects this run (daily-chunk batching to stay
    under the Groq token ceiling). Operational only — does not affect the frozen config."""
    print("\nEvent Probability Engine — Signal Run")
    print(f"Running signal extraction (arm: {'gated' if GATE_ENABLED else 'ungated'}"
          f"{f', limit {limit}' if limit else ''})...\n")

    cache = load_cache()

    # Score FIRST so subjects whose predictions are due today are freed and re-predicted in this
    # same run (otherwise re-prediction lags a full run behind scoring).
    from score import run_scorer
    print("Auto-scoring any predictions due today...")
    run_scorer()

    predictions = load_predictions()  # reload — scorer just mutated the file

    done = 0
    for subject in load_subjects():
        if limit is not None and done >= limit:
            print(f"\nReached limit ({limit}) — stopping this run. Remaining subjects next run.")
            break
        if not subject.get('active', True):
            print(f"\nSkipping {subject['name']} — inactive (waiting for batch).")
            continue
        already_pending = any(
            p['subject'] == subject['name'] and p.get('outcome') is None
            for p in predictions
        )
        if already_pending:
            print(f"\nSkipping {subject['name']} — prediction already pending.")
            continue

        try:
            record = run_subject(subject, cache, predictions)
        except Exception as e:
            print(f"  Subject failed ({e}) — skipping, rest of batch continues.")
            continue
        if record:
            predictions.append(record)
            _append_prediction_entry(record)
            save_predictions(predictions)
            done += 1

    print(f"\n{'='*50}")
    print(f"Done. {len(predictions)} prediction(s) saved to state/predictions.json")


def rerun_subject_forced(subject_name):
    """Re-evaluate a single subject regardless of pending status. Called when a new source is added."""
    cache = load_cache()
    predictions = load_predictions()
    subjects = load_subjects()
    subject = next((s for s in subjects if s['name'] == subject_name), None)
    if not subject:
        print(f"rerun_subject_forced: subject '{subject_name}' not found")
        return
    record = run_subject(subject, cache, predictions)
    if not record:
        return
    existing = next((p for p in predictions if p['subject'] == subject_name and p.get('outcome') is None), None)
    if existing:
        if record['direction'] != existing['direction']:
            for field in ['signals', 'event', 'direction', 'confidence', 'confidence_reason', 'timeframe', 'contra', 'reasoning']:
                existing[field] = record[field]
            existing['source_triggered_update'] = True
            print(f"  Prediction updated: now {existing['direction'].upper()} (source-triggered flip)")
        else:
            print(f"  Direction unchanged ({existing['direction']}), prediction kept.")
    else:
        predictions.append(record)
        _append_prediction_entry(record)  # genuinely new prediction — log it like main() does
    save_predictions(predictions)


if __name__ == "__main__":
    import sys
    _limit = None
    if '--limit' in sys.argv:
        _limit = int(sys.argv[sys.argv.index('--limit') + 1])
    main(limit=_limit)
