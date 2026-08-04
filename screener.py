import csv
import io
import time

import requests

from sma import sma, pct_distance

SP500_CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"


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


if __name__ == "__main__":
    tickers = get_sp500_tickers()
    print(len(tickers))

    results = []
    failed = []

    for i, ticker in enumerate(tickers):
        try:
            results.append(get_stock_data(ticker))
        except Exception:
            failed.append(ticker)

        if i % 20 == 0:
            time.sleep(1)

    print(len(results))
    print(len(failed))
    print(failed)
