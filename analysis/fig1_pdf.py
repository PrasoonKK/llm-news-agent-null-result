#!/usr/bin/env python3
"""Vector PDF of Figure 1 from paper/results.json (same numbers as paper/fig1.svg). Needs matplotlib. Grayscale-safe."""
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'paper')
r = json.load(open(os.path.join(P, 'results.json')))['fixed']
rows = [('Pipeline', r['pipeline']), ('Always DOWN', r['always_down']), ('Coin flip (up/down)', r['coin_ud']),
        ('Coin flip (3-way)', r['coin_udn']), ('Always NEUTRAL', r['always_neutral']), ('Always UP', r['always_up'])]
plt.rcParams['axes.titlesize'] = 9
fig, (a, b) = plt.subplots(1, 2, figsize=(8.2, 3.2), gridspec_kw={'width_ratios': [1.3, 1]})
y = range(len(rows))[::-1]
a.barh(list(y), [v for _, v in rows], color=['0.15'] + ['0.7'] * 5, hatch=None)
a.set_yticks(list(y), [n for n, _ in rows])
for yi, (_, v) in zip(y, rows):
    a.text(v + 1, yi, f'{v}%', va='center', fontsize=8)
a.set(xlim=(0, 75), xlabel='accuracy (%)', title=f'(a) Accuracy, ±2% band (n={r["n"]})')
lo, hi = r['neutral_ci']
b.errorbar([r['neutral_acc']], [0], xerr=[[r['neutral_acc'] - lo], [hi - r['neutral_acc']]], fmt='ko', capsize=4)
b.axvline(r['base_rate'], color='0.4', ls='--')
b.text(r['base_rate'], 0.35, f'base rate {r["base_rate"]}%', ha='center', fontsize=8)
b.text(r['neutral_acc'], -0.3, f'neutral calls {r["neutral_acc"]}%\n95% CI [{lo}, {hi}] (n={r["n_neutral"]})', ha='center', fontsize=8)
b.set(xlim=(20, 60), ylim=(-0.8, 0.8), yticks=[], xlabel='accuracy (%)', title='(b) Neutral calls vs base rate')
fig.tight_layout()
fig.savefig(os.path.join(P, 'fig1.pdf'))
