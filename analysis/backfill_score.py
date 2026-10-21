#!/usr/bin/env python3
"""Backfill scorer: score overdue predictions against the CLOSE PRICE ON THEIR check_date
(the intended window), not today's price. Mirrors score.py's rule: up=move>0, down=move<0,
neutral=|move|<=2%. Uses the real current date."""
import json, os, sys
from datetime import datetime, timedelta
import yfinance as yf

PRED = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'predictions.json')
NEUTRAL_BAND = 2.0
TODAY = datetime.now().strftime('%Y-%m-%d')

def close_on(ticker, check_date, cache):
    if ticker not in cache:
        cd = datetime.strptime(check_date, '%Y-%m-%d')
        start = (cd - timedelta(days=7)).strftime('%Y-%m-%d')
        end = (cd + timedelta(days=7)).strftime('%Y-%m-%d')
        try:
            h = yf.Ticker(ticker).history(start=start, end=end)
            cache[ticker] = [(d.strftime('%Y-%m-%d'), float(c)) for d, c in zip(h.index, h['Close']) if c == c]
        except Exception as e:
            print(f"  warn {ticker}: {e}"); cache[ticker] = []
    rows = cache[ticker]
    if not rows: return None
    on_before = [(d, c) for d, c in rows if d <= check_date]
    return on_before[-1][1] if on_before else rows[0][1]

def main(apply=False):
    preds = json.load(open(PRED))
    due = [p for p in preds if p.get('outcome') is None and p.get('check_date','') <= TODAY]
    print(f"backfilling {len(due)} overdue (<= {TODAY}) at check_date price\n")
    cache = {}; scored = skipped = 0
    for p in due:
        t, base, d, cd = p.get('ticker'), p.get('baseline_price'), p.get('direction'), p['check_date']
        if not t or not base: print(f"  SKIP {p['subject']}: no ticker/baseline"); skipped += 1; continue
        price = close_on(t, cd, cache)
        if price is None: print(f"  SKIP {p['subject']}: no price near {cd}"); skipped += 1; continue
        move = (price - base) / base * 100
        ok = move > 0 if d == 'up' else move < 0 if d == 'down' else abs(move) <= NEUTRAL_BAND
        outcome = 'correct' if ok else 'incorrect'
        print(f"  {p['subject']:14} {d.upper():8} {cd} base={base} close={round(price,2)} move={move:+.1f}% -> {outcome.upper()}")
        if apply:
            p['outcome'] = outcome; p['outcome_price'] = round(price, 2); p['outcome_date'] = cd
        scored += 1
    print(f"\n{'APPLIED' if apply else 'DRY RUN'}: {scored} scored, {skipped} skipped")
    if apply:
        json.dump(preds, open(PRED, 'w'), indent=2); print("saved.")

if __name__ == '__main__':
    main(apply='--apply' in sys.argv)
