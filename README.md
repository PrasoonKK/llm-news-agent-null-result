# EP Engine — a prospective negative result

A multi-agent LLM news pipeline, evaluated prospectively with frozen prompts on 230 scored predictions (55 assets,
logged 29 Aug – 3 Oct 2026), collapses to near-constant abstention: it calls NEUTRAL 85% of the time and its overall accuracy
(39.6%) matches the constant "always neutral" predictor (40.0%). Its 34 directional calls were 38.2% correct (95% bootstrap CI
23.5–55.9%, p = 0.23), too few to say anything firm. We found no evidence of edge, with limited power to detect a modest one.

**Paper:** [`paper/paper.md`](paper/paper.md) · Preprint link: _TBD_
Author: Prasoon Kumar Kashyap (Manipal Institute of Technology, Bengaluru).

## Reproduce the numbers (no API keys needed)
```bash
pip install -r requirements.txt
python3 analysis/final_results.py      # -> paper/results.json, paper/fig1.svg
python3 analysis/power.py              # power of the 34-call directional test
python3 baseline.py --version 1.0-frozen
python3 analysis/mechanism.py --version 1.0-frozen   # needs internet (yfinance)
```
Each script has a `--test` self-check where applicable. Exploratory (not pre-registered): `analysis/exploratory_risk_coverage.py`.

## Data: `state/predictions.json`
One list of prediction records. Frozen study records have `pipeline_version == "1.0-frozen"` and
`config_hash == "ee2fcffc74f5"` (hash of the 5 prompts + 2 model IDs); records without `pipeline_version` are the exploratory pilot and
are excluded from every confirmatory number. Fields: `id, subject, ticker, category, arm (gated|ungated), date_logged, check_date,
baseline_price, neutral_sigma (daily-return σ in %), signals, event, direction (up|down|neutral), confidence (low|medium|high),
confidence_reason, contra, reasoning, timeframe, tier, outcome (correct|incorrect), outcome_price, outcome_date`.
Scoring: UP correct if price rose, DOWN if it fell, NEUTRAL if |move| ≤ 2% over 7 days (5 for crypto); overdue items are scored at
their check-date close.

## Re-run the pipeline (needs your own keys, uses LLM tokens)
Copy `.env.example` to `.env`, add keys, then `python3 pipeline.py --limit 12`. Editing prompts or models changes the config
hash and breaks comparability with the frozen set.

## Layout
`pipeline.py` predict · `score.py` score · `baseline.py`, `analysis/` results · `docs/` protocol + pilot · `paper/` write-up ·
`dashboard/`, `api.py` optional local UI (not needed for the study).

## Cite
```
Kashyap, P. K. (2026). A Multi-Agent LLM News Pipeline Collapses to Near-Constant Abstention and Shows No Detectable Edge:
A Prospective Negative Result. Preprint.
```

Not financial advice or a trading tool. _License: none chosen yet (suggestion: MIT for code, CC-BY-4.0 for data)._
