import csv
import io
import os
import time

import requests

from sma import sma, pct_distance

SP500_CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
TOP_N = 20


def get_sp500_tickers():
    response = requests.get(SP500_CSV_URL)
    reader = csv.DictReader(io.StringIO(response.text))
    return [row["Symbol"] for row in reader]


def get_stock_data(ticker):
    yahoo_ticker = ticker.replace(".", "-")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}?range=1y&interval=1d"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    data = response.json()
    result = data["chart"]["result"][0]
    price = result["meta"]["regularMarketPrice"]
    closes = result["indicators"]["quote"][0]["close"]
    average = sma(closes, 150)
    distance = pct_distance(price, average)
    return {"ticker": ticker, "price": price, "average": average, "distance": distance}


def scan_all(tickers):
    results = []
    failed = []
    for i, ticker in enumerate(tickers):
        try:
            results.append(get_stock_data(ticker))
        except Exception:
            failed.append(ticker)
        if i % 20 == 0:
            time.sleep(1)
    return results, failed


def get_top_n(results, n=TOP_N):
    return sorted(results, key=lambda r: abs(r["distance"]))[:n]


def print_table(entries):
    print(f"{'Ticker':<8}{'Price':>10}{'SMA150':>10}{'Dist %':>10}")
    for e in entries:
        print(f"{e['ticker']:<8}{e['price']:>10.2f}{e['average']:>10.2f}{e['distance']:>+9.2f}%")


def send_alert(entries):
    worker_url = os.environ.get("SCREENER_WORKER_URL")
    secret = os.environ.get("SCREENER_SECRET")
    if not worker_url or not secret:
        print("SCREENER_WORKER_URL / SCREENER_SECRET not set - skipping WhatsApp send, printed table only.")
        return

    payload = [
        {"ticker": e["ticker"], "price": e["price"], "average": e["average"], "distance": e["distance"]}
        for e in entries
    ]
    response = requests.post(
        f"{worker_url}/screener-alert",
        headers={"X-Screener-Secret": secret, "Content-Type": "application/json"},
        json=payload,
    )
    response.raise_for_status()
    print("Sent to WhatsApp worker.")


if __name__ == "__main__":
    tickers = get_sp500_tickers()
    print(f"{len(tickers)} tickers in S&P 500")

    results, failed = scan_all(tickers)
    print(f"{len(results)} succeeded, {len(failed)} failed: {failed}")

    top20 = get_top_n(results)
    print_table(top20)

    send_alert(top20)
