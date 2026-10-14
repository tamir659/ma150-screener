import time

import requests

from fibonacci import fib_level, find_best_swing
from screener import _worker_credentials, get_sp500_tickers

MIN_RALLY_PCT = 30  # "strong, sharp" rally - matches the common >30% screening convention
# Weekly candles over 5 years (changed from 6mo/daily at the user's request, 2026-10-14) -
# catches major multi-year swings instead of smaller moves inside the last 6 months. A
# recently-listed ticker (spinoff/IPO) just gets however much history actually exists -
# Yahoo returns what it has rather than erroring, which is the right behavior here.
LOOKBACK_RANGE = "5y"
INTERVAL = "1wk"


def get_fibonacci_data(ticker):
    yahoo_ticker = ticker.replace(".", "-")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}?range={LOOKBACK_RANGE}&interval={INTERVAL}"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    data = response.json()
    result = data["chart"]["result"][0]
    price = result["meta"]["regularMarketPrice"]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]

    swing = find_best_swing(closes)
    if swing is None:
        return None
    rally_pct, swing_low, _, swing_high, _ = swing

    return {
        "ticker": ticker,
        "price": price,
        "swing_low": swing_low,
        "swing_high": swing_high,
        "rally_pct": rally_pct,
        "fib618": fib_level(swing_low, swing_high, 0.618),
        "fib65": fib_level(swing_low, swing_high, 0.65),
    }


def scan_all_fibonacci(tickers):
    results = []
    failed = []
    for i, ticker in enumerate(tickers):
        try:
            data = get_fibonacci_data(ticker)
            if data is not None:
                results.append(data)
        except Exception:
            failed.append(ticker)
        if i % 20 == 0:
            time.sleep(1)
    return results, failed


def get_candidates(results, min_rally_pct=MIN_RALLY_PCT):
    # The "golden pocket": price sitting between the 65% and 61.8% retracement levels,
    # after a rally big enough to call "strong and sharp" rather than noise.
    qualifying = [
        r for r in results
        if r["rally_pct"] >= min_rally_pct and r["fib65"] <= r["price"] <= r["fib618"]
    ]
    qualifying.sort(key=lambda r: r["rally_pct"], reverse=True)  # biggest rallies first
    return qualifying


def print_table(candidates):
    print(f"{'Ticker':<8}{'Price':>10}{'Low':>10}{'High':>10}{'Rally':>9}{'Fib618':>10}")
    for c in candidates:
        print(f"{c['ticker']:<8}{c['price']:>10.2f}{c['swing_low']:>10.2f}{c['swing_high']:>10.2f}"
              f"{c['rally_pct']:>+8.1f}%{c['fib618']:>10.2f}")


def send_alert(candidates):
    worker_url, secret, phone_number = _worker_credentials()
    if not worker_url or not secret or not phone_number:
        print("SCREENER_WORKER_URL / SCREENER_SECRET / PHONE_NUMBER not set - skipping send, printed table only.")
        return

    payload = {
        "to": phone_number,
        "kind": "fibonacci",
        "entries": [
            {
                "ticker": c["ticker"],
                "price": c["price"],
                "swingLow": c["swing_low"],
                "swingHigh": c["swing_high"],
                "rallyPct": c["rally_pct"],
                "fib618": c["fib618"],
            }
            for c in candidates
        ],
    }
    response = requests.post(
        f"{worker_url}/screener-alert",
        headers={"X-Screener-Secret": secret, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    print(f"Sent fibonacci alert to worker for {phone_number} ({len(candidates)} candidate(s)).")


def send_error(message):
    worker_url, secret, phone_number = _worker_credentials()
    if not worker_url or not secret or not phone_number:
        print(f"SCREENER_WORKER_URL / SCREENER_SECRET / PHONE_NUMBER not set - can't send error "
              f"notification. Error was: {message}")
        return
    try:
        response = requests.post(
            f"{worker_url}/screener-alert",
            headers={"X-Screener-Secret": secret, "Content-Type": "application/json"},
            json={"to": phone_number, "kind": "fibonacci", "error": message},
            timeout=30,
        )
        response.raise_for_status()
        print(f"Sent failure notice to worker for {phone_number}.")
    except Exception as notify_err:
        print(f"Also failed to send the error notification itself: {notify_err}. Original error: {message}")


if __name__ == "__main__":
    try:
        tickers = get_sp500_tickers()
        print(f"{len(tickers)} tickers in S&P 500")

        results, failed = scan_all_fibonacci(tickers)
        print(f"{len(results)} succeeded, {len(failed)} failed: {failed}")

        candidates = get_candidates(results)
        print(f"{len(candidates)} candidate(s) in the golden pocket")
        print_table(candidates)

        send_alert(candidates)
    except Exception as e:
        print(f"Fibonacci screener run failed: {e}")
        send_error(str(e))
        raise
