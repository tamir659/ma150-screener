import os
from datetime import datetime, timedelta

import requests

FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"
MAX_HEADLINES = 5


def get_recent_news(ticker, days=14):
    token = (os.environ.get("FINNHUB_KEY") or "").strip()
    if not token:
        return []

    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=days)

    response = requests.get(
        FINNHUB_NEWS_URL,
        params={
            "symbol": ticker,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "token": token,
        },
        timeout=15,
    )
    response.raise_for_status()
    articles = response.json()

    return [
        {"headline": a["headline"], "summary": a.get("summary", "")}
        for a in articles[:MAX_HEADLINES]
    ]


if __name__ == "__main__":
    for item in get_recent_news("AAPL"):
        print(item["headline"])
