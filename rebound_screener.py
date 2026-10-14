import time

import requests

from claude_client import analyze_candidates
from news import get_recent_news
from rsi import rsi
from screener import _worker_credentials, get_sp500_tickers

ATH_DROP_THRESHOLD = -30  # at least 30% below all-time high
RSI_OVERSOLD_THRESHOLD = 30  # classic oversold RSI line
MAX_CANDIDATES = 5  # deep-dive report, not a 20-line table - each one gets news + an AI writeup


def get_ath_data(ticker):
    yahoo_ticker = ticker.replace(".", "-")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}?range=max&interval=1mo"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    data = response.json()
    result = data["chart"]["result"][0]
    price = result["meta"]["regularMarketPrice"]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
    ath = max(closes)
    pct_below_ath = (price - ath) / ath * 100
    return price, ath, pct_below_ath


def get_rsi_value(ticker):
    yahoo_ticker = ticker.replace(".", "-")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}?range=1mo&interval=1d"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    data = response.json()
    closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    return rsi(closes, period=14)


def get_rebound_data(ticker):
    price, ath, pct_below_ath = get_ath_data(ticker)
    rsi_value = get_rsi_value(ticker)
    return {"ticker": ticker, "price": price, "ath": ath, "pct_below_ath": pct_below_ath, "rsi": rsi_value}


def scan_all_rebound(tickers):
    results = []
    failed = []
    for i, ticker in enumerate(tickers):
        try:
            results.append(get_rebound_data(ticker))
        except Exception:
            failed.append(ticker)
        if i % 20 == 0:
            time.sleep(1)
    return results, failed


def get_candidates(results, ath_drop_threshold=ATH_DROP_THRESHOLD, rsi_threshold=RSI_OVERSOLD_THRESHOLD,
                    max_candidates=MAX_CANDIDATES):
    qualifying = [r for r in results if r["pct_below_ath"] <= ath_drop_threshold and r["rsi"] < rsi_threshold]
    qualifying.sort(key=lambda r: r["rsi"])  # most oversold first
    return qualifying[:max_candidates]


def print_table(candidates):
    print(f"{'Ticker':<8}{'Price':>10}{'ATH':>10}{'Below ATH':>12}{'RSI':>8}")
    for c in candidates:
        print(f"{c['ticker']:<8}{c['price']:>10.2f}{c['ath']:>10.2f}{c['pct_below_ath']:>+11.2f}%{c['rsi']:>8.1f}")


def send_alert(candidates, analyses):
    worker_url, secret, phone_number = _worker_credentials()
    if not worker_url or not secret or not phone_number:
        print("SCREENER_WORKER_URL / SCREENER_SECRET / PHONE_NUMBER not set - skipping send, printed table only.")
        return

    payload = {
        "to": phone_number,
        "kind": "rebound",
        "entries": [
            {
                "ticker": c["ticker"],
                "price": c["price"],
                "pctBelowAth": c["pct_below_ath"],
                "rsi": c["rsi"],
                "analysis": analyses.get(c["ticker"], "No analysis available."),
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
    print(f"Sent rebound alert to worker for {phone_number} ({len(candidates)} candidate(s)).")


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
            json={"to": phone_number, "kind": "rebound", "error": message},
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

        results, failed = scan_all_rebound(tickers)
        print(f"{len(results)} succeeded, {len(failed)} failed: {failed}")

        candidates = get_candidates(results)
        print(f"{len(candidates)} candidate(s) matched the thresholds")
        print_table(candidates)

        analyses = {}
        if candidates:
            for c in candidates:
                c["news"] = get_recent_news(c["ticker"])
            analyses = analyze_candidates(candidates)

        send_alert(candidates, analyses)
    except Exception as e:
        print(f"Rebound screener run failed: {e}")
        send_error(str(e))
        raise
