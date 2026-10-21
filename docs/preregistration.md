# Pre-Registration — Frozen Confirmatory Study

**Registered:** 2026-08-28 · **Revised:** 2026-09-01 · **Author:** Prasoon Kumar Kashyap (Manipal Institute of Technology, Bengaluru)
**Target output:** arXiv preprint (q-fin.ST / cs.CE), later submitted to a workshop (e.g. ICAIF).

This document is written and timestamped **before** collecting the confirmatory data. It fixes the
hypotheses, configuration, metrics, target sample size, and stopping rule. Deviations, if any, will
be reported as such.

**Revision note (2026-09-01), made before any confirmatory outcome existed:** subject list expanded
33 → 55 and the default arm set to ungated (Arm A), purely to raise throughput and directional volume
so the target N is reachable within the 12-week cap. This revision is legitimate under pre-registration
because **no frozen prediction had been scored yet** — the one gated batch of 2026-08-30 (33 records,
all NEUTRAL) was still pending and could not have informed the change. The prompts, models, and
`config_hash` are unchanged. Those 33 gated records remain valid Arm-B data.

---

## Frozen configuration (do not change during collection)

- `PIPELINE_VERSION = "1.0-frozen"` (stamped on every prediction record)
- `config_hash = ee2fcffc74f5` (MD5 of the exact prompts + model IDs; auto-checked per record)
- Models: `openai/gpt-oss-120b` (mapper/synthesizer/predictor/fallback), `openai/gpt-oss-20b` (researchers)
- Reasoning effort: low · temperature: 0.3 · max_tokens: 2200 (large) / 1200 (small)
- Subjects: the 55 in `state/subjects.json` (as of 2026-09-01) — liquid large-caps across sectors,
  major commodities, major crypto, a few international. Selection criterion: liquid + well-covered by
  news; chosen before any outcomes existed.
- Check windows: crypto 5 days, all else 7 days (per `check_after_days`)

**Any change to prompts, models, or subjects bumps `PIPELINE_VERSION` and ends the frozen run.**
Confirmatory analysis includes only records with `pipeline_version == "1.0-frozen"` and the matching
`config_hash`.

---

## Hypotheses

**Reframe note (2026-09-01, before any frozen outcome existed):** the pilot and the first frozen
batches show the pipeline overwhelmingly abstains — it calls NEUTRAL the large majority of the time
even ungated. The primary claim is therefore reframed around *value added over naive baselines*, of
which directional accuracy is one component. This is a framing change, not a data change; no
confirmatory prediction had been scored when it was made.

- **H1 (primary):** The pipeline adds no value over naive baselines across the decisions it makes.
  Two parts, both on the identical prediction set (`baseline.py`):
  - (a) Overall accuracy does not exceed the best naive baseline (always-UP / always-DOWN /
    always-NEUTRAL / coin-flip).
  - (b) **Neutral-timing skill:** neutral-call accuracy does not exceed the base rate of flatness
    (what "always neutral" scores) — i.e. the pipeline does not choose *when* to abstain any better
    than abstaining always. Report accuracy + 95% bootstrap CI vs the base rate.
- **H2 (directional):** Among UP/DOWN calls, directional accuracy is not greater than 50%.
  Two-sided exact binomial vs 0.5 + 95% CI. Reported with its N; if the ungated arm yields few
  directional calls, this is reported as an underpowered secondary result, not suppressed.
- **H3 (mechanism):** The pipeline chases prior 3-day momentum (chase rate > 50%) and that momentum
  reverses (> 50%), explaining any sub-chance directional accuracy. (`analysis/mechanism.py`)

## Two arms

- **Arm A — ungated** (`EP_GATE=off`, now the DEFAULT): raw LLM directional calls. Primary arm for
  H1/H3 (max directional volume). The gated arm produced 0 directional calls in its one batch, so
  the bulk of collection runs ungated.
- **Arm B — gated** (`EP_GATE=on`): catalyst gate active. Run occasionally for the A-vs-B comparison
  (does the deterministic gate add value?). Both arms stamped on records via the `arm` field.

Collection cadence: run in daily chunks of ~10–12 subjects (`python3 pipeline.py --limit 12`) to stay
under the Groq daily token ceiling; each subject re-predicts only once its prior prediction scores.

## Metrics & scoring

- Primary: directional accuracy (UP/DOWN only), with 95% CI and binomial p vs 50%.
- Secondary: overall accuracy vs baselines; per-arm and per-category breakdowns.
- **Neutral band, pre-specified both ways** (robustness): (a) fixed ±2% (legacy); (b) volatility-scaled,
  correct if |move| ≤ σ·√(window_days), σ = `neutral_sigma` stored at prediction time. Both reported;
  neither is chosen post hoc.

## Sample size & stopping rule

- Target: **~500 total predictions → ≈200 directional calls in Arm A** (power to distinguish 40% from 50%).
- Cadence: 55 subjects, each re-predicting ~weekly → ~55 predictions/week run in daily chunks. Ungated
  arm yields directional calls on a large fraction of predictions, so ~200 directional is reachable in ~5–6 weeks.
- **Stopping rule (original):** stop at 500 total predictions under the frozen config OR at
  12 weeks from registration (2026-11-20), whichever comes first.
- **Stopping rule (revised 2026-09-09, deviation — documented for integrity):** collection ends
  **2026-10-07** (~4 weeks out), then write-up begins, at an expected ~330 frozen predictions rather
  than 500. Rationale: (a) the primary result — near-total abstention with neutral-timing skill
  indistinguishable from the always-neutral base rate — is already stable and consistent across the
  pilot (n=179) and frozen data (n≈60), so additional weeks add power, not new information; (b) this
  is a *null* result, so stopping earlier only REDUCES statistical power (a more conservative claim) —
  it cannot inflate significance, which is the failure mode pre-registration guards against. The end
  date is fixed now and committed; no further peeking-and-stopping. Interim results were seen before
  this revision and this is disclosed as a deviation, not concealed.

## Analysis plan (locked)

1. Filter to frozen-config records. 2. `baseline.py` → H1, H2 with CIs. 3. `analysis/mechanism.py` → H3.
4. Robustness: repeat under both neutral-band definitions. 5. Report Arm A vs Arm B.
6. Limitations reported regardless: bull/bear regime of the window, retail-data scope, subject
   selection, single 1–7 day horizon, non-peer-reviewed model behavior.

## Reproducibility

Full code + `state/predictions.json` published with the writeup. Analysis scripts are deterministic
(fixed bootstrap seed). Pilot (pre-freeze) results in `docs/pilot_findings.md`, kept separate and
labeled exploratory.
</content>

---

## Outcome addendum (2026-10-13)

Collection ended 2026-10-07 as revised. Final frozen set: **230 scored predictions** (32 gated, 198 ungated),
**34 directional** — below both the ~330 expected at the revised stop and the original 500 / ~200 directional
targets. The gated arm contains 32 records (not 33 as stated above). One record lacks a stored `neutral_sigma`
and is excluded from the vol-scaled robustness check only. The protocol was self-filed in this folder and never
registered with an independent registry, so its timestamps are not externally verifiable.
Results: `paper/results.json` (from `analysis/final_results.py`); write-up: `paper/paper.md`.
