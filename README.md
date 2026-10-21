# Does an LLM news agent predict markets? A prospective test

Many people are building AI agents that read the news and call whether a stock will go up or down. This repository tests one such system properly: every prediction was logged before the outcome existed, and the prompts and models were frozen for the whole study. The code, the data and the report are all here.

**Short answer: we found no evidence that it works.**

- The agent made 230 scored predictions on 55 assets (stocks, ETFs, commodities, crypto) over about six weeks.
- It said "neutral" 85% of the time. Its overall accuracy (39.6%) matched the lazy strategy of always saying "neutral" (40.0%).
- Its 34 "up" or "down" calls were right 38.2% of the time. That sample is too small to conclude anything (95% CI 23.5–55.9%).

This is a result for one system, in one falling market, over a short window. It does not show that no AI system can ever predict markets, and with so few directional calls the study could only have detected a very large edge. The report is open about these limits and lists every deviation from the original plan.

**Report:** `paper/paper.md`
**Author:** Prasoon Kumar Kashyap, Manipal Institute of Technology, Bengaluru

## How the system works

For each asset, a pipeline of language-model calls (`gpt-oss-120b` and `gpt-oss-20b` via Groq) lists the outside factors that could move the price, searches Google News for each, scores the signals, and outputs UP, DOWN or NEUTRAL. Each call is scored against the real closing price 5–7 days later. See the report for the full setup.

## Reproduce the results

You don't need any API keys. The data is included.

```bash
git clone https://github.com/PrasoonKK/ep-engine-negative-result
cd ep-engine-negative-result
pip install -r requirements.txt
python3 analysis/final_results.py   # regenerates every number in the report
python3 analysis/power.py           # how big an edge 34 calls could detect
python3 baseline.py --version 1.0-frozen
```

Two optional scripts: `analysis/mechanism.py` (momentum analysis, needs internet) and `analysis/exploratory_risk_coverage.py` (exploratory, not part of the pre-specified analysis).

## The data

`state/predictions.json` holds every prediction and its outcome.

- **Study records** have `pipeline_version == "1.0-frozen"` and `config_hash == "ee2fcffc74f5"`. This is the set every number in the report comes from.
- **Pilot records** have no `pipeline_version`. They are an earlier exploratory run and are excluded from all study results.
- **Main fields:** `subject`, `category`, `date_logged`, `check_date`, `direction` (up/down/neutral), `confidence`, `baseline_price`, `outcome_price`, `outcome` (correct/incorrect).
- **Scoring:** UP is correct if the price rose, DOWN if it fell, NEUTRAL if it moved less than 2% over 7 days (5 days for crypto).

## Run the pipeline yourself

This needs your own API keys and uses LLM tokens. Copy `.env.example` to `.env`, add your Groq and Finnhub keys, then run `python3 pipeline.py --limit 12`. Changing the prompts or models breaks comparison with the study data.

## What's in the repo

| Path | Contents |
|---|---|
| `paper/` | the report, figures and computed results |
| `analysis/`, `baseline.py` | analysis scripts |
| `pipeline.py`, `score.py` | the prediction system and scorer |
| `state/` | data |
| `docs/` | the study protocol and pilot findings |
| `dashboard/`, `api.py` | an optional local web UI, not needed for the study |

This is research code, not financial advice or a trading tool.
