#!/usr/bin/env python3
"""Final numbers + figure for the preprint. Frozen set only, no tokens, deterministic.

Usage: python3 analysis/final_results.py   -> prints results, writes paper/results.json + paper/fig1.svg
"""
import json
import math
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from baseline import binom_two_sided_p, bootstrap_ci, load_scored, NEUTRAL_BAND  # reuse, don't re-implement

FROZEN_HASH = 'ee2fcffc74f5'  # config_hash of the frozen prompts + models (pipeline.py)
OUT = os.path.join(os.path.dirname(__file__), '..', 'paper')
pct = lambda a, b: round(100 * a / b, 1) if b else None


def ok(call, move, band):
    return move > 0 if call == 'up' else move < 0 if call == 'down' else abs(move) <= band


def band_of(p, mode):
    if mode == 'fixed':
        return NEUTRAL_BAND
    w = 5 if p['category'] == 'crypto' else 7  # check_after_days per pre-registration
    return p['neutral_sigma'] * math.sqrt(w)


def evaluate(S, mode):
    """Accuracy of pipeline + baselines on S under a neutral-band definition."""
    n = len(S)
    pipe = [ok(p['direction'], p['_move_pct'], band_of(p, mode)) for p in S]
    r = {'n': n, 'pipeline': pct(sum(pipe), n)}
    for name in ('up', 'down', 'neutral'):
        r['always_' + name] = pct(sum(ok(name, p['_move_pct'], band_of(p, mode)) for p in S), n)
    # exact expectation of a fair up/down coin and a fair 3-way coin
    ud = [(ok('up', p['_move_pct'], 0) + ok('down', p['_move_pct'], 0)) / 2 for p in S]
    r['coin_ud'] = pct(sum(ud), n)
    r['coin_udn'] = pct(sum(ud) * 2 / 3 + sum(ok('neutral', p['_move_pct'], band_of(p, mode)) for p in S) / 3, n)
    neu = [(p, f) for p, f in zip(S, pipe) if p['direction'] == 'neutral']
    flat = [ok('neutral', p['_move_pct'], band_of(p, mode)) for p in S]
    k, m = sum(f for _, f in neu), len(neu)
    r.update(n_neutral=m, neutral_acc=pct(k, m), neutral_ci=bootstrap_ci([int(f) for _, f in neu]),
             base_rate=pct(sum(flat), n))
    # not-called-neutral flat rate: if skill existed, the pipeline's NON-neutral cases would be less flat
    rest = [fl for (p, fl) in zip(S, flat) if p['direction'] != 'neutral']
    r['flat_rate_when_directional'] = pct(sum(rest), len(rest))
    # exact hypergeometric: P(>=k flat among m neutral picks) if the m picks were random from n
    K, N = sum(flat), n
    r['hypergeom_p_one_sided'] = round(sum(math.comb(K, i) * math.comb(N - K, m - i) for i in range(k, min(K, m) + 1))
                                       / math.comb(N, m), 3) if m else None
    # cluster bootstrap by logging date (assets move together): flat-rate of neutral-called minus directional-called cases.
    # (Neutral-acc minus overall base rate would be mechanically tight since neutral calls are ~85% of the data.)
    by = defaultdict(list)
    for p, fl in zip(S, flat):
        by[p['date_logged']].append((p['direction'] == 'neutral', fl))
    keys, rng, diffs = list(by), random.Random(99), []
    for _ in range(4000):
        rows = [x for _ in keys for x in by[keys[rng.randrange(len(keys))]]]
        a, b = [x[1] for x in rows if x[0]], [x[1] for x in rows if not x[0]]
        if a and b:
            diffs.append(100 * (sum(a) / len(a) - sum(b) / len(b)))
    diffs.sort()
    r['cluster_diff_ci'] = ([round(diffs[int(.025 * len(diffs))], 1), round(diffs[int(.975 * len(diffs))], 1)]
                            if diffs else None)  # gated arm has no directional calls
    r['n_clusters'] = len(keys)
    return r


def directional(S):
    D = [p for p in S if p['direction'] in ('up', 'down')]
    flags = [int(p['outcome'] == 'correct') for p in D]
    k, n = sum(flags), len(flags)
    out = {'n': n, 'k': k, 'acc': pct(k, n), 'ci': bootstrap_ci(flags), 'p': round(binom_two_sided_p(k, n), 3)}
    for d in ('up', 'down'):
        sub = [p for p in D if p['direction'] == d]
        out[d] = {'n': len(sub), 'k': sum(p['outcome'] == 'correct' for p in sub)}
    return out


def fig(r, path):
    """Two-panel SVG: strategy accuracy bars, neutral-call accuracy vs base rate with CI."""
    bars = [('Pipeline', r['pipeline']), ('Always DOWN', r['always_down']), ('Coin flip (up/down)', r['coin_ud']),
            ('Coin flip (3-way)', r['coin_udn']), ('Always NEUTRAL', r['always_neutral']), ('Always UP', r['always_up'])]
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 330" font-family="Helvetica,Arial,sans-serif" font-size="12">',
         '<rect width="760" height="330" fill="white"/>',
         '<text x="10" y="18" font-weight="bold">(a) Overall accuracy vs naive baselines (n=%d)</text>' % r['n']]
    for i, (name, v) in enumerate(bars):
        y = 35 + i * 40
        col = '#c0392b' if i == 0 else '#8a96a3'
        s.append(f'<text x="10" y="{y+17}">{name}</text><rect x="150" y="{y}" width="{v*3.2:.0f}" height="24" fill="{col}"/>'
                 f'<text x="{155+v*3.2:.0f}" y="{y+17}">{v}%</text>')
    # panel b
    x0, sc = 560, 2.0
    s.append('<text x="470" y="18" font-weight="bold">(b) Neutral calls vs base rate</text>')
    lo, hi = r['neutral_ci']
    s.append(f'<line x1="480" y1="260" x2="740" y2="260" stroke="black"/>')
    for t in (20, 30, 40, 50, 60):
        x = 480 + (t - 20) * 6.5
        s.append(f'<line x1="{x}" y1="260" x2="{x}" y2="265" stroke="black"/><text x="{x-8}" y="280">{t}%</text>')
    X = lambda v: 480 + (v - 20) * 6.5
    s.append(f'<line x1="{X(r["base_rate"])}" y1="40" x2="{X(r["base_rate"])}" y2="260" stroke="#2c7fb8" stroke-dasharray="5,4"/>'
             f'<text x="{X(r["base_rate"])-70}" y="55" fill="#2c7fb8">base rate {r["base_rate"]}%</text>')
    s.append(f'<line x1="{X(lo)}" y1="150" x2="{X(hi)}" y2="150" stroke="#c0392b" stroke-width="3"/>'
             f'<circle cx="{X(r["neutral_acc"])}" cy="150" r="6" fill="#c0392b"/>'
             f'<text x="{X(lo)}" y="135" fill="#c0392b">neutral calls {r["neutral_acc"]}% [{lo}, {hi}]</text>')
    s.append('</svg>')
    open(path, 'w').write('\n'.join(s))


def main():
    S = [p for p in load_scored(version='1.0-frozen') if p.get('config_hash') == FROZEN_HASH]
    res = {'n': len(S), 'fixed': evaluate(S, 'fixed'), 'volscaled': evaluate([p for p in S if p.get('neutral_sigma')], 'vol'),  # 1 record lacks sigma
           'directional': directional(S)}
    res['arms'] = {a: evaluate([p for p in S if p['arm'] == a], 'fixed') for a in ('ungated', 'gated')}
    res['categories'] = {c: evaluate([p for p in S if p['category'] == c], 'fixed')
                         for c in sorted({p['category'] for p in S})}
    res['pct_moves_negative'] = pct(sum(p['_move_pct'] < 0 for p in S), len(S))
    res['dates'] = [min(p['date_logged'] for p in S), max(p['date_logged'] for p in S)]
    res['n_subjects'] = len({p['subject'] for p in S})
    pilot = [p for p in load_scored() if not p.get('pipeline_version')]
    res['pilot_n'] = len(pilot)
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, 'results.json'), 'w'), indent=1)
    fig(res['fixed'], os.path.join(OUT, 'fig1.svg'))
    print(json.dumps(res, indent=1))


def _demo():
    S = [{'direction': 'neutral', 'outcome': 'correct', '_move_pct': 1, 'category': 'stock', 'neutral_sigma': 1,
          'date_logged': 'a'},
         {'direction': 'up', 'outcome': 'incorrect', '_move_pct': -3, 'category': 'stock', 'neutral_sigma': 1,
          'date_logged': 'b'}]
    r = evaluate(S, 'fixed')
    assert r['pipeline'] == 50.0 and r['always_neutral'] == 50.0 and r['always_down'] == 50.0
    print('self-check passed')


if __name__ == '__main__':
    _demo() if '--test' in sys.argv else main()
