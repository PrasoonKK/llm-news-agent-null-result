# Event Probability Engine

A personal market-prediction tracker. It monitors ~55 subjects (stocks, ETFs, commodities, crypto), reads recent news, feeds it to an LLM alongside structured market data, makes a directional call (UP / DOWN / NEUTRAL), logs it with the baseline price, then scores it against the real price after the check window. Accuracy is tracked over time and fed back into future prompts.

Personal use only — no selling, no publishing.

**Last updated:** 2026-08-15

---

## Run it

```bash
cd ep_engine_release  # repo root
./run.sh                       # starts API (:8000) + dashboard (:5174), Ctrl+C stops both
```

```bash
python3 pipeline.py            # generate predictions for all active subjects, then auto-score due ones
python3 score.py               # score predictions whose check_date has arrived
python3 score.py --force       # score immediately, ignore check_date
python3 backtest.py            # refresh per-ticker signal calibration → state/calibration.json
```

Dashboard: **http://localhost:5174**. Cron (if installed) runs `pipeline.py` daily and logs to `state/cron.log`.

---

## Files

```
ep_engine/
├── pipeline.py       Main pipeline: fetch news → structured signals → LLM → predict → log → auto-score
├── score.py          Scorer: compares outcome price vs baseline, marks correct/incorrect
├── api.py            FastAPI backend (:8000) — serves predictions/stats, scoring, add-subject, sources
├── backtest.py       Per-ticker momentum/volume/RSI base-rate backtest → calibration.json
├── run.sh            Launches API + dashboard together
├── .env              API keys — NEVER commit
├── dashboard/        React + Vite + Tailwind frontend (:5174), UI lives in src/App.jsx
├── reports/          Append-only human-readable log of every prediction + scoring
│   ├── prediction_report.md
│   └── scoring_report.md
├── state/            Live data — do not hand-edit
│   ├── subjects.json         Subject configs
│   ├── predictions.json      Single source of truth: every prediction + outcome
│   ├── calibration.json      Backtest base rates per ticker (from backtest.py)
│   ├── sources_library.json  Reusable RSS source presets for the dashboard
│   ├── llm_cache.json        LLM response cache, MD5-keyed, 7-day auto-purge
│   └── cron.log
└── docs/README.md    This file
```

---

## How a prediction is made

For each subject, `run_subject()` in pipeline.py assembles context, then runs a **4-call multi-agent pipeline** (falls back to a single LLM call if any step fails):

1. **Factor Mapper** (70b) — lists 5 external factors that could move the subject.
2. **Factor Researchers** (8b ×5) — fetch Google News RSS per factor, summarize what's relevant.
3. **Signal Synthesizer** (70b) — scores every signal 1–3, drops score-1 noise.
4. **Predictor** (70b) — outputs UP/DOWN/NEUTRAL from the pre-filtered signals.

Structured data injected into the prompt (all deterministic, not LLM-guessed):

| Signal | Source |
|--------|--------|
| Fresh news (last 48h, date-labeled) | Finnhub + Google News RSS |
| 3-day price momentum | yfinance |
| Volume anomaly (>2× 10-day avg) | yfinance |
| Upcoming earnings (≤14 days) | yfinance calendar |
| VIX regime (calm vs elevated) | yfinance ^VIX |
| Crypto Fear & Greed | alternative.me |
| Insider buy/sell clusters | Finnhub |
| Analyst consensus | Finnhub |
| Historical signal calibration | calibration.json (from backtest.py) |
| Past accuracy feedback + last 3 outcomes | predictions.json |

**Forced rules:** predict UP/DOWN only when 2+ qualifying signals agree; otherwise NEUTRAL. Must state the strongest counter-argument (`contra`) before committing.

---

## Scoring

`score.py` runs automatically at the end of every pipeline run, and scores anything past its `check_date`:

- **UP** — correct if outcome price > baseline
- **DOWN** — correct if outcome price < baseline
- **NEUTRAL** — correct if |change| ≤ 2%
- **shortage / surplus** — flagged manual (legacy, unused by current subjects)

Earnings push: if earnings fall inside the check window, `check_date` auto-extends to the day after earnings so the catalyst is captured.

---

## Subjects & timing

~33 active subjects, all `timeline_mode: custom`. Crypto uses a **5-day** check window (fast movers); everything else uses **7 days**. Add a subject via the dashboard or by appending to `subjects.json`. TPD (tokens-per-day) on Groq is per-model and rolling-24h, so batches of ~10 subjects/day are the safe cadence to cover all 33 without exhausting quota.

---

## Infrastructure — all free tier

| Component | Tool | Notes |
|-----------|------|-------|
| LLM (predict/synthesize) | Groq `llama-3.3-70b-versatile` | TPD-limited, rolling 24h |
| LLM (factor research) | Groq `llama-3.1-8b-instant` | separate TPD quota |
| Prices | yfinance | no key |
| Financial news + insider + analyst | Finnhub | key in .env |
| General news | Google News RSS | no key |
| Backend | FastAPI + uvicorn (:8000) | |
| Frontend | React + Vite + Tailwind (:5174) | |

**Keys in `.env`:** `GROQ_API_KEY`, `FINNHUB_API_KEY`, `POLYGON_API_KEY` (reserved, unused). Never commit `.env`.

---

## Current state (2026-10-13)

Study complete. **230 frozen predictions scored, 55 subjects, 39.6% accuracy vs 40.0% always-neutral;**
85% of calls are NEUTRAL, 34 directional calls at 38.2% (CI spans 50%). Negative result — see `paper/paper.md`.
Models are now `openai/gpt-oss-120b` / `gpt-oss-20b` (the Llama references above are historical), and
cron is disabled (collection is manual). Regenerate all paper numbers: `python3 analysis/final_results.py`.
Never publish `.env` or `state/llm_cache.json`; release only code, `docs/`, `paper/` and `state/predictions.json`.
