# Improvement Backlog

Grounded in the 149 scored predictions as of 2026-08-15. Ranked by leverage-per-effort.

## The core finding

Directional (UP/DOWN) accuracy is **42.7%** — *below* a coin flip. Confidence is
uncalibrated (high 50% / med 43% / low 45%). The LLM reading news to call direction
has no measurable edge. The only signals with any grounding are the *deterministic*
ones (earnings calendar, momentum base rates, insider clusters, volume spikes).
Everything below follows from that.

---

## 1. Volatility-scaled NEUTRAL band  (~15 lines, highest leverage)

**Problem:** NEUTRAL is scored correct only if |move| ≤ 2%, fixed across all assets.
Bitcoin moves 2% before lunch; JPMorgan barely moves 2% in a week. Median move on
NEUTRAL calls is 2.5% over the 7-day window, so half of them fail on noise alone.

**Fix:** define "no significant move" per asset. At prediction time, store the stddev
of daily returns (`σ`, from the 10-day history already fetched in
`get_momentum_context`). Score NEUTRAL correct when |move| ≤ σ·√(window_days). That is
the natural 1-sigma expected move — statistically correct, not goalpost-moving.

**Expected:** NEUTRAL 46%→~60%, overall 44%→~50%+. Note: this changes historical
numbers, so rescore once and treat it as a new baseline.

---

## 2. Gate directional calls on a hard catalyst; abstain otherwise

**Problem:** the pipeline forces a call on every subject every run. Directional calls
are at chance, so 75 coin-flips drag the whole system down.

**Fix:** only *permit* UP/DOWN when a deterministic catalyst is present —
earnings inside the window, OR momentum aligned with a >55% backtest base rate from
calibration.json, OR a 2+ insider cluster. No hard catalyst → force NEUTRAL. This
shrinks directional volume to the subset where we might actually have edge and stops
the LLM from guessing.

**Measure:** directional accuracy on the gated subset vs the current 42.7%. If it
doesn't clear ~55%, the news pipeline isn't adding value and #3 will prove it.

---

## 3. Null-model baseline scorer  (~40 lines — the measurement that gates everything)

**Problem:** there's no benchmark. Is 44% good or bad? Unknown.

**Fix:** `baseline.py` replays the same scored set and reports what dumb strategies
would have scored on identical predictions: always-neutral, always-up, momentum-follow,
momentum-reverse (per calibration), coin-flip. If the LLM pipeline can't beat
"always-neutral with the vol band," the news pipeline is decoration — stop investing in
prompts and lean entirely on structured signals.

Run this before/after every future change. It's the honest scoreboard.
</content>
