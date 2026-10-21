#!/usr/bin/env python3
"""EXPLORATORY - not pre-registered. Selective-prediction view of the abstention finding. Frozen set only.

Stored per-prediction score: `confidence` in {low, medium, high} (categorical, so ties; no probability stored).
(1) Operating point: coverage = directional calls / all, selective accuracy = accuracy on those calls, compared with the
    accuracy of random same-size subsets of all 230 (permutation, seed 2026, 10,000 draws).
(2) Risk-coverage over the directional calls: admit calls from highest confidence tier downward; selective accuracy at each
    tier cutoff vs random same-size subsets of the directional calls.
Writes paper/exploratory_risk_coverage.json and paper/fig_risk_coverage.pdf (needs matplotlib; skipped if absent).
Usage: python3 analysis/exploratory_risk_coverage.py
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from baseline import load_scored

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'paper')
DRAWS, SEED, TIERS = 10000, 2026, ('high', 'medium', 'low')


def perm(flags, k, rng):
    """Accuracy (%) of DRAWS random k-subsets of flags."""
    return sorted(100 * sum(rng.sample(flags, k)) / k for _ in range(DRAWS))


def summarize(obs, dist):
    """Where obs falls in the permutation distribution: percentile + one-sided p of doing at least this well."""
    return {'observed': round(obs, 1), 'perm_mean': round(sum(dist) / len(dist), 1),
            'perm_95ci': [round(dist[int(.025 * DRAWS)], 1), round(dist[int(.975 * DRAWS)], 1)],
            'percentile': round(100 * sum(x < obs for x in dist) / DRAWS, 1),
            'p_at_least': round(sum(x >= obs for x in dist) / DRAWS, 3)}


def main():
    S = load_scored(version='1.0-frozen')
    ok = lambda p: int(p['outcome'] == 'correct')
    D = [p for p in S if p['direction'] in ('up', 'down')]
    res = {'label': 'EXPLORATORY - not pre-registered', 'seed': SEED, 'draws': DRAWS, 'n_all': len(S), 'n_directional': len(D)}
    rng = random.Random(SEED)
    k, acc = len(D), 100 * sum(map(ok, D)) / len(D)
    res['operating_point'] = {'coverage_pct': round(100 * k / len(S), 1), 'selective_accuracy': round(acc, 1),
                              **summarize(acc, perm([ok(p) for p in S], k, rng))}
    curve = []
    for i, t in enumerate(TIERS):
        sub = [p for p in D if p['confidence'] in TIERS[:i + 1]]
        if sub and (not curve or len(sub) != curve[-1]['n']):
            a = 100 * sum(map(ok, sub)) / len(sub)
            curve.append({'confidence_cutoff': f'>= {t}', 'n': len(sub), 'coverage_of_directional_pct': round(100 * len(sub) / k, 1),
                          'selective_accuracy': round(a, 1), **summarize(a, perm([ok(p) for p in D], len(sub), rng))})
    res['by_confidence_tier_cumulative'] = curve
    res['tier_counts_directional'] = {t: sum(p['confidence'] == t for p in D) for t in TIERS}
    res['tier_accuracy_directional'] = {t: [sum(map(ok, [p for p in D if p['confidence'] == t])), res['tier_counts_directional'][t]] for t in TIERS}
    json.dump(res, open(os.path.join(OUT, 'exploratory_risk_coverage.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('matplotlib not installed: skipped paper/fig_risk_coverage.pdf')
        return
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    xs = [c['coverage_of_directional_pct'] for c in curve]
    ax.plot(xs, [c['selective_accuracy'] for c in curve], 'ko-', label='pipeline (by confidence tier)')
    ax.fill_between(xs, [c['perm_95ci'][0] for c in curve], [c['perm_95ci'][1] for c in curve], color='0.8', label='random subsets, 95%')
    ax.axhline(50, color='0.5', ls=':', lw=1)
    ax.set(xlabel='coverage of the 34 directional calls (%)', ylabel='selective accuracy (%)', ylim=(0, 100),
           title='EXPLORATORY - not pre-registered', xlim=(0, 105))
    ax.legend(fontsize=7, loc='lower left')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_risk_coverage.pdf'))


def _demo():
    d = perm([1, 0] * 5, 5, random.Random(1))
    assert len(d) == DRAWS and 0 <= d[0] <= d[-1] <= 100
    s = summarize(50.0, d)
    assert 0 <= s['percentile'] <= 100 and s['p_at_least'] > 0
    print('self-check passed')


if __name__ == '__main__':
    _demo() if '--test' in sys.argv else main()
