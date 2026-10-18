# S&P 500 Stock Screeners

Python screeners that scan all ~500 S&P 500 stocks for technical setups and send the results
to a Telegram bot ([whatsapp-stock-bot](https://github.com/tamir659/whatsapp-stock-bot)).
They run on demand as **GitHub Actions** workflows, triggered from the bot.

## Screeners

| Screener | Script | What it finds |
|----------|--------|---------------|
| **Moving-average proximity** | `screener.py` | The 20 stocks closest to their 150-day (or 20-day) simple moving average |
| **Oversold rebound** | `rebound_screener.py` | Stocks ≥30% below their all-time high with RSI < 30, enriched with recent news and an AI-generated summary |
| **Fibonacci "golden pocket"** | `fibonacci_screener.py` | Stocks that rallied ≥30% and pulled back to the 61.8% retracement level (5 years of weekly candles) |

The rebound and Fibonacci screeners skip stocks with an earnings report coming up soon, since an
earnings surprise can override the technical signal.

## How it works

1. A user sends a command to the Telegram bot.
2. The bot triggers the matching workflow through the GitHub API (`workflow_dispatch`).
3. The workflow fetches price history from Yahoo Finance, computes the indicators and ranks
   the results.
4. Results are POSTed back to the bot's Worker with a shared secret and delivered to the chat.

## Tech stack

- Python 3.12, `requests`
- Yahoo Finance chart API (price history), Finnhub (earnings calendar, company news)
- Claude API for short written analysis of rebound candidates
- GitHub Actions for on-demand execution

## Project structure

```
fetch.py               # price history from Yahoo Finance
sma.py                 # simple moving average + % distance
rsi.py                 # RSI calculation
fibonacci.py           # swing detection and retracement levels
earnings.py            # next earnings date (Finnhub)
news.py                # recent headlines (Finnhub)
claude_client.py       # AI summary of candidates
screener.py            # SMA proximity screener + S&P 500 ticker list
rebound_screener.py    # oversold-rebound screener
fibonacci_screener.py  # Fibonacci retracement screener
.github/workflows/     # on-demand workflows for each screener
```

## Running locally

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python screener.py             # prints the results table
```

Without the bot environment variables the scripts just print their results. Delivery needs
`SCREENER_WORKER_URL` and `SCREENER_SECRET`; the rebound screener also uses `FINNHUB_KEY` and
`ANTHROPIC_API_KEY`. All of these are GitHub Actions secrets, not stored in the repository.

> For learning and research only — not financial advice.
