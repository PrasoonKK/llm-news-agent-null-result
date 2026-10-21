#!/usr/bin/env python3
"""
Mechanism analysis (H3): does the pipeline chase already-priced-in momentum that then reverses?

For each directional prediction we recompute the prior 3-day price move at the time the prediction
was logged (not stored on the record, so fetched from yfinance history), then ask:
  1. Chase rate  — how often does the call direction match the sign of the prior 3-day move?
  2. Does chasing pay — accuracy when the call agrees with prior momentum vs when it fights it.
  3. Does momentum reverse — sign of the prior move vs sign of the realized outcome move.

Usage: python3 analysis/mechanism.py         # real analysis (network: yfinance)
       python3 analysis/mechanism.py --test  # offline self-check of the math
"""

import os
import sys
import json
from datetime import datetime, timedelta

_DIR = os.path.dirname(os.path.dirname(__file__))
PREDICTIONS_FILE = os.path.join(_DIR, 'state', 'predictions.json')


def load_usable(version=None):
    with open(PREDICTIONS_FILE) as f:
        preds = json.load(f)
    return [
        p for p in preds
        if p.get('outcome') in ('correct', 'incorrect')
        and p.get('ticker') and p.get('baseline_price') and p.get('outcome_price')
        and p.get('date_logged')
        and (version is None or p.get('pipeline_version') == version)
    ]


def prior_move_lookup(preds):
    """Returns {prediction_id: prior_3d_move_pct}. Fetches each ticker's history once."""
    import yfinance as yf
    tickers = sorted(set(p['ticker'] for p in preds))
    dates = sorted(p['date_logged'] for p in preds)
    start = (datetime.strptime(dates[0], '%Y-%m-%d') - timedelta(days=20)).strftime('%Y-%m-%d')
    end = (datetime.strptime(dates[-1], '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')

    out = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(start=start, end=end)
        except Exception as e:
            print(f"  warn: {t} history failed ({e})")
            continue
        if hist.empty:
            continue
        closes = [(d.strftime('%Y-%m-%d'), float(c)) for d, c in zip(hist.index, hist['Close'])]
        for p in (x for x in preds if x['ticker'] == t):
            # last trading day on or before date_logged
            idx = max((i for i, (d, _) in enumerate(closes) if d <= p['date_logged']), default=None)
            if idx is None or idx < 3:
                continue
            now = closes[idx][1]
            past = closes[idx - 3][1]
            if past:
                out[p['id']] = (now - past) / past * 100
    return out


def sign(x, dead=0.0):
    if x > dead:
        return 'up'
    if x < -dead:
        return 'down'
    return 'flat'


def report(preds, prior):
    dir_preds = [p for p in preds if p.get('direction') in ('up', 'down') and p['id'] in prior]
    print(f"\nMechanism analysis — {len(dir_preds)} directional predictions with recoverable prior momentum\n")

    # 1. Chase rate
    chased = [p for p in dir_preds if p['direction'] == sign(prior[p['id']])]
    against = [p for p in dir_preds if sign(prior[p['id']]) != 'flat' and p['direction'] != sign(prior[p['id']])]
    n_nonflat = len(chased) + len(against)
    if n_nonflat:
        print(f"1. CHASE RATE: call matched the prior 3-day move direction in "
              f"{len(chased)}/{n_nonflat} = {round(len(chased)/n_nonflat*100)}% of cases")
        print(f"   (>50% means the pipeline tends to predict continuation of the move that already happened)")

    # 2. Does chasing pay
    def acc(group):
        return round(sum(1 for p in group if p['outcome'] == 'correct') / len(group) * 100) if group else None
    print(f"\n2. DOES CHASING PAY:")
    print(f"   When call CHASED prior momentum: {acc(chased)}% correct (n={len(chased)})")
    print(f"   When call FOUGHT prior momentum: {acc(against)}% correct (n={len(against)})")

    # 3. Does momentum reverse (all usable preds, not just directional)
    rev = [p for p in preds if p['id'] in prior]
    reversed_ct = same_ct = 0
    for p in rev:
        pm = sign(prior[p['id']])
        om = sign((p['outcome_price'] - p['baseline_price']) / p['baseline_price'] * 100)
        if pm == 'flat' or om == 'flat':
            continue
        if pm == om:
            same_ct += 1
        else:
            reversed_ct += 1
    tot = reversed_ct + same_ct
    if tot:
        print(f"\n3. DOES PRIOR MOMENTUM REVERSE (all assets, n={tot}):")
        print(f"   Prior move CONTINUED same direction: {same_ct}/{tot} = {round(same_ct/tot*100)}%")
        print(f"   Prior move REVERSED:                 {reversed_ct}/{tot} = {round(reversed_ct/tot*100)}%")
        print(f"   (>50% reversal = chasing momentum is structurally a losing bet on these assets)")

    print("\nInterpretation: if chase rate >50% AND reversal >50%, the pipeline is systematically")
    print("betting on continuation of moves that tend to mean-revert — a concrete failure mechanism.\n")


def _test():
    # Synthetic: 2 preds, known prior moves, verify chase/sign logic.
    preds = [
        {'id': 'a', 'direction': 'up',   'baseline_price': 100, 'outcome_price': 95,  'outcome': 'incorrect'},
        {'id': 'b', 'direction': 'down', 'baseline_price': 100, 'outcome_price': 105, 'outcome': 'incorrect'},
    ]
    prior = {'a': 5.0, 'b': 4.0}  # 'a' chased up-momentum, 'b' fought up-momentum
    assert sign(5.0) == 'up' and sign(-1.0) == 'down' and sign(0.0) == 'flat'
    chased = [p for p in preds if p['direction'] == sign(prior[p['id']])]
    assert len(chased) == 1 and chased[0]['id'] == 'a'
    print("self-check passed")


if __name__ == '__main__':
    if '--test' in sys.argv:
        _test()
    else:
        version = sys.argv[sys.argv.index('--version') + 1] if '--version' in sys.argv else None
        if version:
            print(f"[filtered to pipeline_version={version}]")
        preds = load_usable(version=version)
        prior = prior_move_lookup(preds)
        report(preds, prior)
