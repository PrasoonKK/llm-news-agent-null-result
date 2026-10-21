import os
import json
import yfinance as yf
from dotenv import load_dotenv
from datetime import datetime

_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(_DIR, '.env'))

PREDICTIONS_FILE = os.path.join(_DIR, 'state', 'predictions.json')
REPORTS_DIR = os.path.join(_DIR, 'reports')


def _append_scoring_entry(p, change_pct):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    price_line = (
        f"${p['baseline_price']} → ${p['outcome_price']} ({change_pct:+.2f}%)"
        if p.get('baseline_price') and p.get('outcome_price')
        else 'N/A'
    )
    signals = ', '.join(p.get('signals', [])) or 'N/A'
    entry = (
        f"## {p['subject']} — {p['outcome'].upper()} | {p['outcome_date']}\n\n"
        f"- **Predicted:** {p['direction'].upper()} on {p['date_logged']} (confidence: {p['confidence']})\n"
        f"- **Price:** {price_line}\n"
        f"- **Original Signals:** {signals}\n"
        f"- **Contra:** {p.get('contra', 'N/A')}\n\n---\n\n"
    )
    with open(os.path.join(REPORTS_DIR, 'scoring_report.md'), 'a') as f:
        f.write(entry)


def load_predictions():
    with open(PREDICTIONS_FILE) as f:
        return json.load(f)


def save_predictions(predictions):
    with open(PREDICTIONS_FILE, 'w') as f:
        json.dump(predictions, f, indent=2)


def get_current_price(ticker):
    if not ticker:
        return None
    try:
        data = yf.Ticker(ticker)
        price = data.fast_info.last_price
        return round(price, 2) if price else None
    except Exception:
        return None


def score_prediction(prediction, current_price):
    baseline = prediction.get('baseline_price')
    direction = prediction.get('direction', '').lower()

    if baseline is None or current_price is None:
        return None, "no_price_data"

    change_pct = ((current_price - baseline) / baseline) * 100

    if direction in ('up',):
        correct = current_price > baseline
    elif direction in ('down',):
        correct = current_price < baseline
    elif direction == 'neutral':
        correct = abs(change_pct) <= 2.0
    elif direction in ('shortage', 'surplus'):
        return None, "manual_check_needed"
    else:
        return None, "unknown_direction"

    return correct, round(change_pct, 2)


def run_scorer(force=False):
    predictions = load_predictions()
    today = datetime.now().strftime('%Y-%m-%d')
    scored_count = 0
    skipped_count = 0
    pending_count = 0

    print("\nEvent Probability Engine — Outcome Scorer")
    print(f"Running on: {today}\n")

    for p in predictions:
        subject = p['subject']
        check_date = p.get('check_date')
        outcome = p.get('outcome')

        if outcome is not None:
            print(f"[ALREADY SCORED] {subject} — {outcome.upper()}")
            skipped_count += 1
            continue

        if not force and today < check_date:
            days_left = (datetime.strptime(check_date, '%Y-%m-%d') - datetime.now()).days
            print(f"[PENDING] {subject} — check date is {check_date} ({days_left} days away)")
            pending_count += 1
            continue

        ticker = p.get('ticker')
        current_price = get_current_price(ticker)

        print(f"\n{'='*50}")
        print(f"Scoring: {subject}")
        print(f"{'='*50}")
        print(f"  Prediction:    {p['direction'].upper()} within {p['timeframe']}")
        print(f"  Baseline:      {'$' + str(p['baseline_price']) if p['baseline_price'] else 'N/A'}")
        print(f"  Current price: {'$' + str(current_price) if current_price else 'N/A'}")

        correct, detail = score_prediction(p, current_price)

        if correct is None:
            if detail == "manual_check_needed":
                print(f"  Result:        MANUAL CHECK NEEDED (direction: {p['direction']})")
                p['outcome'] = 'manual'
                p['outcome_price'] = current_price
                p['outcome_date'] = today
            elif detail == "no_price_data":
                print(f"  Result:        SKIPPED — no price data available")
            else:
                print(f"  Result:        SKIPPED — {detail}")
        else:
            outcome_str = 'correct' if correct else 'incorrect'
            print(f"  Change:        {'+' if detail > 0 else ''}{detail}%")
            print(f"  Result:        {'CORRECT' if correct else 'INCORRECT'}")
            p['outcome'] = outcome_str
            p['outcome_price'] = current_price
            p['outcome_date'] = today
            _append_scoring_entry(p, detail)
            scored_count += 1

    save_predictions(predictions)

    print(f"\n{'='*50}")
    print("Summary")
    print(f"{'='*50}")

    scored = [p for p in predictions if p.get('outcome') in ('correct', 'incorrect')]
    correct = [p for p in scored if p['outcome'] == 'correct']

    if scored:
        accuracy = round(len(correct) / len(scored) * 100, 1)
        print(f"  Scored:    {len(scored)} predictions")
        print(f"  Correct:   {len(correct)}")
        print(f"  Incorrect: {len(scored) - len(correct)}")
        print(f"  Accuracy:  {accuracy}%")
        print()
        for p in scored:
            icon = "✓" if p['outcome'] == 'correct' else "✗"
            change = ""
            if p['baseline_price'] and p['outcome_price']:
                chg = round(((p['outcome_price'] - p['baseline_price']) / p['baseline_price']) * 100, 2)
                change = f" ({'+' if chg > 0 else ''}{chg}%)"
            print(f"  {icon} {p['subject']} — predicted {p['direction'].upper()}{change}")
    else:
        print(f"  No predictions scored yet.")
        if pending_count:
            print(f"  {pending_count} prediction(s) still pending their check date.")

    print()


if __name__ == "__main__":
    import sys
    force = '--force' in sys.argv
    if force:
        print("(Force mode — scoring regardless of check date)")
    run_scorer(force=force)
