#!/usr/bin/env python3
"""
Baseline scorer — replays the same scored predictions.json against dumb strategies
to answer: is the LLM pipeline actually better than doing nothing?

Usage: python3 baseline.py
"""

import os
import json
import math
import random
import statistics

_DIR = os.path.dirname(__file__)
PREDICTIONS_FILE = os.path.join(_DIR, 'state', 'predictions.json')

NEUTRAL_BAND = 2.0  # matches score.py's current definition


def binom_two_sided_p(k, n, p=0.5):
    """Exact two-sided binomial test p-value: P(outcome at least as extreme as k) under Binom(n, p)."""
    pmf = [math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(n + 1)]
    obs = pmf[k]
    return min(1.0, sum(x for x in pmf if x <= obs + 1e-12))


def bootstrap_ci(correct_flags, iters=5000, level=0.95):
    """95% bootstrap CI for the mean of a 0/1 list. Deterministic seed for reproducibility."""
    rng = random.Random(1234)
    n = len(correct_flags)
    if n == 0:
        return (None, None)
    means = []
    for _ in range(iters):
        s = sum(correct_flags[rng.randrange(n)] for _ in range(n))
        means.append(s / n * 100)
    means.sort()
    lo = means[int((1 - level) / 2 * iters)]
    hi = means[int((1 + level) / 2 * iters)]
    return (round(lo, 1), round(hi, 1))


def load_scored(version=None, arm=None):
    """version/arm: optional filters to isolate the frozen confirmatory set from the pilot 182."""
    with open(PREDICTIONS_FILE) as f:
        preds = json.load(f)
    scored = [
        p for p in preds
        if p.get('outcome') in ('correct', 'incorrect')
        and p.get('baseline_price') and p.get('outcome_price')
        and (version is None or p.get('pipeline_version') == version)
        and (arm is None or p.get('arm') == arm)
    ]
    for p in scored:
        p['_move_pct'] = (p['outcome_price'] - p['baseline_price']) / p['baseline_price'] * 100
    return scored


def acc(scored, predict_fn, trials=1):
    """predict_fn(p) -> 'up' | 'down' | 'neutral'. Averages over `trials` runs (for randomized strategies)."""
    runs = []
    for _ in range(trials):
        correct = 0
        for p in scored:
            call = predict_fn(p)
            move = p['_move_pct']
            if call == 'up':
                ok = move > 0
            elif call == 'down':
                ok = move < 0
            else:
                ok = abs(move) <= NEUTRAL_BAND
            correct += ok
        runs.append(correct / len(scored) * 100)
    return round(statistics.mean(runs), 1)


def main(version=None, arm=None):
    scored = load_scored(version=version, arm=arm)
    n = len(scored)
    if n == 0:
        print(f"\nNo scored predictions match filter (version={version}, arm={arm}).\n")
        return
    tag = f" [version={version}]" if version else ""
    tag += f" [arm={arm}]" if arm else ""
    print(f"\nBaseline Scorer — replaying {n} scored predictions{tag}\n")

    actual_correct = sum(1 for p in scored if p['outcome'] == 'correct')
    actual_acc = round(actual_correct / n * 100, 1)

    strategies = {
        'Always NEUTRAL':      lambda p: 'neutral',
        'Always UP':           lambda p: 'up',
        'Always DOWN':         lambda p: 'down',
    }

    results = {name: acc(scored, fn) for name, fn in strategies.items()}
    # ponytail: coin flips as exact expected values (mean of the constant strategies), not an unseeded simulation
    u, d, nn = results['Always UP'], results['Always DOWN'], results['Always NEUTRAL']
    results['Coin flip (up/down)'] = round((u + d) / 2, 1)
    results['Coin flip (u/d/n)'] = round((u + d + nn) / 3, 1)

    print(f"{'Strategy':<24} {'Accuracy':>10}")
    print("-" * 36)
    print(f"{'EP Engine (actual)':<24} {actual_acc:>9}%")
    for name, a in sorted(results.items(), key=lambda x: -x[1]):
        print(f"{name:<24} {a:>9}%")

    best_dumb = max(results.values())
    print()
    if actual_acc > best_dumb:
        print(f"EP Engine beats the best dumb strategy by {round(actual_acc - best_dumb, 1)} points. The pipeline is adding value.")
    else:
        print(f"EP Engine does NOT beat the best dumb strategy ({best_dumb}%). "
              f"The news/LLM pipeline is not measurably better than {[k for k,v in results.items() if v==best_dumb][0]}.")

    # Directional-only test — the core scientific claim (vs 50% coin flip)
    dir_scored = [p for p in scored if p.get('direction') in ('up', 'down')]
    if dir_scored:
        flags = [1 if p['outcome'] == 'correct' else 0 for p in dir_scored]
        n_dir = len(flags)
        k = sum(flags)
        dir_acc = round(k / n_dir * 100, 1)
        lo, hi = bootstrap_ci(flags)
        pval = binom_two_sided_p(k, n_dir)
        print(f"\nDirectional-only (UP/DOWN calls):")
        print(f"  n = {n_dir}, correct = {k}")
        print(f"  Accuracy: {dir_acc}%  [95% CI: {lo}–{hi}%]")
        print(f"  vs 50% coin flip: two-sided binomial p = {pval:.4f}"
              f"{'  (significant at 0.05)' if pval < 0.05 else '  (not significant)'}")
        if hi is not None and hi < 50:
            print(f"  → CI lies entirely below 50%: directional calls are significantly WORSE than chance.")
        elif lo is not None and lo > 50:
            print(f"  → CI lies entirely above 50%: directional calls beat chance.")
        else:
            print(f"  → CI spans 50%: directional accuracy is indistinguishable from chance.")

    # Abstention + neutral-timing-skill — the PRIMARY reframed metric.
    # The pipeline mostly says neutral; the question is whether it says neutral at the RIGHT times,
    # i.e. does its neutral-call accuracy beat the base rate of flatness (what "always neutral" scores)?
    n_neu = sum(1 for p in scored if p['direction'] == 'neutral')
    neu = [p for p in scored if p['direction'] == 'neutral']
    base_rate_flat = round(sum(1 for p in scored if abs(p['_move_pct']) <= NEUTRAL_BAND) / n * 100, 1)
    print(f"\nAbstention & neutral timing skill (PRIMARY metric):")
    print(f"  Pipeline calls NEUTRAL {round(n_neu/n*100)}% of the time ({n_neu}/{n}).")
    if neu:
        neu_flags = [1 if p['outcome'] == 'correct' else 0 for p in neu]
        neu_acc = round(sum(neu_flags) / len(neu) * 100, 1)
        nlo, nhi = bootstrap_ci(neu_flags)
        print(f"  Neutral-call accuracy:        {neu_acc}%  [95% CI: {nlo}–{nhi}%]")
        print(f"  Base rate of flatness (=always-neutral): {base_rate_flat}%")
        edge = round(neu_acc - base_rate_flat, 1)
        if nlo is not None and nlo > base_rate_flat:
            print(f"  → Neutral CI is above the base rate (+{edge}): the pipeline shows real neutral-timing skill.")
        else:
            print(f"  → Neutral accuracy does NOT beat the base rate ({edge:+}): choosing WHEN to say neutral adds no skill.")

    print()


def _demo():
    """Self-check: a scorer that returns 'always neutral' on synthetic small moves must score ~100%."""
    fake = [
        {'baseline_price': 100, 'outcome_price': 101, 'direction': 'neutral', 'outcome': 'correct'},
        {'baseline_price': 100, 'outcome_price': 105, 'direction': 'up', 'outcome': 'correct'},
    ]
    for p in fake:
        p['_move_pct'] = (p['outcome_price'] - p['baseline_price']) / p['baseline_price'] * 100
    assert acc(fake, lambda p: 'neutral') == 50.0  # only the first call is within ±2%
    assert acc(fake, lambda p: 'up') == 100.0
    print("self-check passed")


if __name__ == "__main__":
    import sys
    if '--test' in sys.argv:
        _demo()
    else:
        def _flag(name):
            return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None
        main(version=_flag('--version'), arm=_flag('--arm'))
