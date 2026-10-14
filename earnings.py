import os
from datetime import date, timedelta

import requests

FINNHUB_CALENDAR_URL = "https://finnhub.io/api/v1/calendar/earnings"
LOOKAHEAD_DAYS = 100  # wide enough to reliably catch next-quarter reports


def get_next_earnings_date(ticker):
    token = (os.environ.get("FINNHUB_KEY") or "").strip()
    if not token:
        return None

    today = date.today()
    response = requests.get(
        FINNHUB_CALENDAR_URL,
        params={
            "from": today.isoformat(),
            "to": (today + timedelta(days=LOOKAHEAD_DAYS)).isoformat(),
            "symbol": ticker,
            "token": token,
        },
        timeout=15,
    )
    response.raise_for_status()
    entries = response.json().get("earningsCalendar", [])
    dates = sorted(e["date"] for e in entries if e.get("date"))
    return dates[0] if dates else None


def days_until(date_str):
    return (date.fromisoformat(date_str) - date.today()).days


if __name__ == "__main__":
    d = get_next_earnings_date("MGM")
    print(d, days_until(d) if d else None)
