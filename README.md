# EP Engine: a prospective negative result

An LLM news pipeline that predicts short-term market direction shows no detectable edge. In a frozen-configuration test on 230 scored predictions (55 assets, 29 Aug – 3 Oct 2026), it said NEUTRAL 85% of the time and matched the "always neutral" baseline (39.6% vs 40.0%). Its 34 directional calls were 38.2% correct (95% CI 23.5–55.9%), too few to conclude anything.

**Paper:** [`paper/paper.md`](paper/paper.md) · Preprint: _link TBD_
**Author:** Prasoon Kumar Kashyap, Manipal Institute of Technology, Bengaluru

## Reproduce the results

No API keys needed.

```bash
pip install -r requirements.txt
python3 analysis/final_results.py   # all paper numbers -> paper/results.json, paper/fig1.svg
python3 analysis/power.py           # power of the 34-call directional test
python3 baseline.py --version 1.0-frozen
```

Optional: `analysis/mechanism.py --version 1.0-frozen` (needs internet) and `analysis/exploratory_risk_coverage.py` (exploratory, not pre-registered).

## Data

`state/predictions.json` holds every prediction and outcome.

- **Study records:** `pipeline_version == "1.0-frozen"` and `config_hash == "ee2fcffc74f5"` (hash of the prompts and model IDs).
- **Pilot records** have no `pipeline_version` and are excluded from all study numbers.
- **Key fields:** `subject`, `category`, `arm`, `date_logged`, `check_date`, `direction` (up/down/neutral), `confidence`, `baseline_price`, `outcome_price`, `outcome` (correct/incorrect).
- **Scoring:** UP is correct if price rose, DOWN if it fell, NEUTRAL if the move was within ±2% over 7 days (5 for crypto).

## Re-run the pipeline

Needs your own keys and uses LLM tokens. Copy `.env.example` to `.env`, add keys, then run `python3 pipeline.py --limit 12`. Changing prompts or models changes the config hash and breaks comparison with the study data.

## Repo layout

| Path | Contents |
|---|---|
| `pipeline.py`, `score.py` | prediction and scoring |
| `baseline.py`, `analysis/` | baselines and paper results |
| `paper/` | write-up, figures, results |
| `docs/` | protocol and pilot findings |
| `state/` | data |
| `dashboard/`, `api.py` | optional local UI, not needed for the study |

## Cite

> Kashyap, P. K. (2026). *A Multi-Agent LLM News Pipeline Collapses to Near-Constant Abstention and Shows No Detectable Edge: A Prospective Negative Result.* Preprint.

Not financial advice or a trading tool.
