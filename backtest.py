#!/usr/bin/env python3
"""
Price signal backtest — validates momentum, volume anomaly, and RSI against 12 months of
historical price data. Saves per-ticker calibration to state/calibration.json for use in prompts.

Usage:
  python3 backtest.py                    # all tickers, 5-day window
  python3 backtest.py --window 10        # test with 10-day prediction window
  python3 backtest.py --ticker TSLA      # single ticker
"""

import os
import json
import argparse
import yfinance as yf
from datetime import datetime

_DIR = os.path.dirname(__file__)
CAL_FILE = os.path.join(_DIR, 'state', 'calibration.json')
SUBJECTS_FILE = os.path.join(_DIR, 'state', 'subjects.json')

# Tickers come straight from subjects.json so backtest coverage never drifts from what we actually predict.
with open(SUBJECTS_FILE) as _f:
    TICKERS = {s['ticker']: s['name'] for s in json.load(_f) if s.get('ticker')}


def compute_rsi(closes, period=14):
    """Wilder's EMA-based RSI. Returns list of RSI values, same length as closes."""
    rsi = [None] * len(closes)
    if len(closes) < period + 1:
        return rsi
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    # Initial averages
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(closes)):
        if i == period:
            pass  # already set above
        else:
            avg_g = (avg_g * (period - 1) + gains[i - 1]) / period
            avg_l = (avg_l * (period - 1) + losses[i - 1]) / period
        rs = avg_g / avg_l if avg_l > 0 else 100
        rsi[i] = round(100 - (100 / (1 + rs)), 1)
    return rsi


def backtest_ticker(ticker, name, lookback_days=365, prediction_window=5, threshold_pct=1.0):
    print(f"  {ticker:10} ({name})...", end=' ', flush=True)
    try:
        hist = yf.Ticker(ticker).history(period=f"{lookback_days + 120}d")
    except Exception as e:
        print(f"ERROR: {e}")
        return None

    if len(hist) < 60:
        print(f"insufficient data ({len(hist)} days)")
        return None

    closes  = [float(x) for x in hist['Close'].tolist()]
    volumes = [float(x) for x in hist['Volume'].tolist()]
    rsi_vals = compute_rsi(closes)

    # Only look at the last `lookback_days` days, with enough future data
    warmup   = 25
    end_idx  = len(closes) - prediction_window
    start_idx = max(warmup, len(closes) - lookback_days - prediction_window)

    def bucket(ret):
        if ret > threshold_pct:   return 'up'
        if ret < -threshold_pct:  return 'down'
        return 'flat'

    # Accumulators
    mom_bull = mom_bear = 0
    mom_bull_n = mom_bear_n = 0
    vol_up = vol_down = vol_flat = vol_n = 0
    rsi_hi_correct = rsi_hi_n = 0
    rsi_lo_correct = rsi_lo_n = 0
    comb_bull = comb_bull_n = 0
    comb_bear = comb_bear_n = 0

    days_tested = 0
    for i in range(start_idx, end_idx):
        c_now    = closes[i]
        c_3d_ago = closes[i - 3] if i >= 3 else c_now
        c_future = closes[i + prediction_window]
        rsi      = rsi_vals[i]

        if c_now == 0 or c_3d_ago == 0:
            continue

        momentum_pct = (c_now - c_3d_ago) / c_3d_ago * 100
        future_ret   = (c_future - c_now) / c_now * 100
        outcome      = bucket(future_ret)

        vol_avg = sum(volumes[max(0, i - 10):i]) / max(min(10, i), 1)
        vol_ratio = volumes[i] / vol_avg if vol_avg > 0 else 1.0

        days_tested += 1

        # Momentum continuation
        if momentum_pct > 2.0:
            mom_bull_n += 1
            if outcome == 'up': mom_bull += 1
        if momentum_pct < -2.0:
            mom_bear_n += 1
            if outcome == 'down': mom_bear += 1

        # Volume anomaly
        if vol_ratio > 2.0:
            vol_n += 1
            if outcome == 'up':   vol_up += 1
            elif outcome == 'down': vol_down += 1
            else: vol_flat += 1

        # RSI extremes (need valid RSI)
        if rsi is not None:
            if rsi > 70:
                rsi_hi_n += 1
                if outcome == 'down': rsi_hi_correct += 1
            if rsi < 30:
                rsi_lo_n += 1
                if outcome == 'up': rsi_lo_correct += 1

        # Combined: momentum + elevated volume (>1.5x)
        if momentum_pct > 2.0 and vol_ratio > 1.5:
            comb_bull_n += 1
            if outcome == 'up': comb_bull += 1
        if momentum_pct < -2.0 and vol_ratio > 1.5:
            comb_bear_n += 1
            if outcome == 'down': comb_bear += 1

    def rate(correct, n): return round(correct / n, 3) if n >= 5 else None

    print(f"done ({days_tested} days)")

    return {
        'ticker':                  ticker,
        'name':                    name,
        'window_days':             prediction_window,
        'lookback_days':           lookback_days,
        'days_tested':             days_tested,
        'generated':               datetime.now().strftime('%Y-%m-%d'),
        'momentum_bull_rate':      rate(mom_bull, mom_bull_n),
        'momentum_bull_n':         mom_bull_n,
        'momentum_bear_rate':      rate(mom_bear, mom_bear_n),
        'momentum_bear_n':         mom_bear_n,
        'volume_up_rate':          rate(vol_up, vol_n),
        'volume_down_rate':        rate(vol_down, vol_n),
        'volume_directional_rate': rate(vol_up + vol_down, vol_n),
        'volume_n':                vol_n,
        'rsi_high_reversal_rate':  rate(rsi_hi_correct, rsi_hi_n),
        'rsi_high_n':              rsi_hi_n,
        'rsi_low_reversal_rate':   rate(rsi_lo_correct, rsi_lo_n),
        'rsi_low_n':               rsi_lo_n,
        'combined_bull_rate':      rate(comb_bull, comb_bull_n),
        'combined_bull_n':         comb_bull_n,
        'combined_bear_rate':      rate(comb_bear, comb_bear_n),
        'combined_bear_n':         comb_bear_n,
    }


def build_calibration_text(s, window):
    """Returns a ready-to-inject prompt string for this ticker, or '' if no strong signals."""
    lines = []
    ticker = s['ticker']

    mbr  = s['momentum_bull_rate']
    mbrn = s['momentum_bull_n']
    mer  = s['momentum_bear_rate']
    mern = s['momentum_bear_n']

    if mbr is not None:
        if mbr >= 0.55:
            lines.append(f"- Positive 3d momentum → continued UP {mbr*100:.0f}% of next-{window}d periods (n={mbrn})")
        elif mbr < 0.45:
            lines.append(f"- Positive 3d momentum REVERSES on this asset — price fell {(1-mbr)*100:.0f}% (mean-reversion, treat bullish momentum as a DOWN signal)")

    if mer is not None:
        if mer >= 0.55:
            lines.append(f"- Negative 3d momentum → continued DOWN {mer*100:.0f}% of next-{window}d periods (n={mern})")
        elif mer < 0.45:
            lines.append(f"- Negative 3d momentum REVERSES — price rose {(1-mer)*100:.0f}% (mean-reversion asset)")

    cbr  = s['combined_bull_rate']
    cbrn = s['combined_bull_n']
    cer  = s['combined_bear_rate']
    cern = s['combined_bear_n']

    if cbr and cbr >= 0.60:
        lines.append(f"- Momentum UP + elevated volume: {cbr*100:.0f}% UP in {window}d (n={cbrn}) — strongest bullish signal")
    if cer and cer >= 0.60:
        lines.append(f"- Momentum DOWN + elevated volume: {cer*100:.0f}% DOWN in {window}d (n={cern}) — strongest bearish signal")

    rhr  = s['rsi_high_reversal_rate']
    rhrn = s['rsi_high_n']
    rlr  = s['rsi_low_reversal_rate']
    rlrn = s['rsi_low_n']

    if rhr and rhr >= 0.58:
        lines.append(f"- RSI>70 (overbought): price fell within {window}d {rhr*100:.0f}% of time (n={rhrn}) — reduce UP confidence")
    elif rhr and rhr < 0.48:
        lines.append(f"- RSI>70 has no reversal power on {ticker} — overbought does NOT mean pullback here")

    if rlr and rlr >= 0.58:
        lines.append(f"- RSI<30 (oversold): price rose within {window}d {rlr*100:.0f}% of time (n={rlrn}) — oversold bounces are reliable")

    if not lines:
        return f"HISTORICAL CALIBRATION ({ticker}): no signal consistently beat 55% over last {s['lookback_days']}d — treat all signals with caution, prefer neutral.\n"

    return (
        f"HISTORICAL SIGNAL CALIBRATION ({ticker}, last {s['lookback_days']}d, {window}d window):\n"
        + "\n".join(lines)
        + "\nUse these base rates to calibrate your confidence. Signals not listed had no predictive power.\n"
    )


def print_report(s, window):
    def fmt(r, n, good_dir='high'):
        if r is None:
            return f"n/a  (n={n}, need ≥5)"
        star = ' ✓' if r >= 0.55 else (' ✗' if r < 0.45 else '')
        return f"{r*100:.0f}%  (n={n}){star}"

    w = window
    print(f"\n{'═'*52}")
    print(f"  {s['name']} ({s['ticker']})  |  {s['days_tested']} days  |  {w}d window")
    print(f"{'═'*52}")
    print(f"  Momentum >+2% → UP next {w}d:   {fmt(s['momentum_bull_rate'], s['momentum_bull_n'])}")
    print(f"  Momentum <-2% → DOWN next {w}d:  {fmt(s['momentum_bear_rate'], s['momentum_bear_n'])}")
    print(f"  Volume >2x avg → directional:  {fmt(s['volume_directional_rate'], s['volume_n'])}")
    print(f"  RSI>70 → DOWN next {w}d:        {fmt(s['rsi_high_reversal_rate'], s['rsi_high_n'])}")
    print(f"  RSI<30 → UP next {w}d:          {fmt(s['rsi_low_reversal_rate'], s['rsi_low_n'])}")
    print(f"  Mom+Vol bullish → UP next {w}d:  {fmt(s['combined_bull_rate'], s['combined_bull_n'])}")
    print(f"  Mom+Vol bearish → DOWN next {w}d:{fmt(s['combined_bear_rate'], s['combined_bear_n'])}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', help='Single ticker (default: all)')
    parser.add_argument('--window', type=int, default=5, help='Prediction window in days (default: 5)')
    parser.add_argument('--days',   type=int, default=365, help='Lookback days (default: 365)')
    args = parser.parse_args()

    tickers = {args.ticker: TICKERS.get(args.ticker, args.ticker)} if args.ticker else TICKERS

    print(f"\nPrice Signal Backtest")
    print(f"Lookback: {args.days} days | Prediction window: {args.window} days")
    print(f"Threshold: ±1% counts as directional move\n")
    print(f"Fetching data...")

    calibration = {}
    if os.path.exists(CAL_FILE):
        with open(CAL_FILE) as f:
            calibration = json.load(f)

    all_stats = []
    for ticker, name in tickers.items():
        stats = backtest_ticker(ticker, name, lookback_days=args.days, prediction_window=args.window)
        if stats:
            print_report(stats, args.window)
            stats['calibration_text'] = build_calibration_text(stats, args.window)
            calibration[ticker] = stats
            all_stats.append(stats)

    with open(CAL_FILE, 'w') as f:
        json.dump(calibration, f, indent=2)

    # Summary table
    print(f"\n\n{'═'*52}")
    print(f"  SUMMARY  (✓ = signal beats 55% baseline)")
    print(f"{'═'*52}")
    for s in all_stats:
        strong = []
        if s['momentum_bull_rate']  and s['momentum_bull_rate']  >= 0.55: strong.append(f"mom↑{s['momentum_bull_rate']*100:.0f}%")
        if s['momentum_bear_rate']  and s['momentum_bear_rate']  >= 0.55: strong.append(f"mom↓{s['momentum_bear_rate']*100:.0f}%")
        if s['combined_bull_rate']  and s['combined_bull_rate']  >= 0.55: strong.append(f"comb↑{s['combined_bull_rate']*100:.0f}%")
        if s['combined_bear_rate']  and s['combined_bear_rate']  >= 0.55: strong.append(f"comb↓{s['combined_bear_rate']*100:.0f}%")
        if s['rsi_high_reversal_rate'] and s['rsi_high_reversal_rate'] >= 0.58: strong.append("RSI↓")
        if s['rsi_low_reversal_rate']  and s['rsi_low_reversal_rate']  >= 0.58: strong.append("RSI↑")
        status = "  ".join(strong) if strong else "no strong signals (prefer neutral)"
        print(f"  {s['ticker']:10}  {status}")

    print(f"\nCalibration saved → state/calibration.json")
    print(f"Run python3 pipeline.py to use calibration in next predictions.\n")


if __name__ == '__main__':
    main()
