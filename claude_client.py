import json
import os

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"
MAX_RETRIES = 2


def _build_prompt(candidates):
    lines = [
        "For each stock below, write a TIGHT, information-dense analysis in AT MOST 2-3 short "
        "sentences - no filler, no hedging phrases, no generic disclaimers, no restating the "
        "numbers already given. Cover only: the likely reason for the drop (if the headlines "
        "indicate one), and a concrete forward-looking angle grounded in those headlines (e.g. "
        "sector narrative like AI exposure for a chip stock). One short closing clause noting "
        "this is informational, not investment advice - nothing more than that.",
        "",
        "Write the analysis text itself in Hebrew. Keep the ticker symbols, company names, and "
        "any numbers in the analysis in Latin characters/digits as usual - only the surrounding "
        "sentences should be Hebrew.",
        "",
        "Respond with ONLY a JSON array, no other text, in this exact shape:",
        '[{"ticker": "AAPL", "analysis": "..."}]',
        "",
    ]
    for c in candidates:
        lines.append(f"## {c['ticker']}")
        lines.append(
            f"Price: ${c['price']:.2f}, {c['pct_below_ath']:.1f}% below all-time high, RSI {c['rsi']:.1f}"
        )
        if c["news"]:
            lines.append("Recent headlines:")
            for item in c["news"]:
                lines.append(f"- {item['headline']}: {item['summary']}")
        else:
            lines.append("No recent headlines found.")
        lines.append("")
    return "\n".join(lines)


# One batched call covering every candidate, rather than one call per ticker - cheaper, faster,
# and lets Claude see all candidates at once (useful if it wants to note relative context).
def analyze_candidates(candidates):
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        return {c["ticker"]: "AI analysis unavailable (no API key configured)." for c in candidates}

    body = {
        "model": MODEL,
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": _build_prompt(candidates)}],
    }

    last_error = None
    for _ in range(MAX_RETRIES + 1):
        response = requests.post(
            API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )
        if response.status_code == 200:
            # claude-sonnet-5 runs adaptive thinking by default even without an explicit
            # "thinking" param, so content[0] is often a "thinking" block, not the text block -
            # scan for the actual text block instead of assuming it's first.
            blocks = response.json()["content"]
            text = next(b["text"] for b in blocks if b.get("type") == "text")
            return _parse_response(text, candidates)
        if response.status_code == 429 or response.status_code >= 500:
            last_error = f"Anthropic API {response.status_code}: {response.text}"
            continue
        raise RuntimeError(f"Anthropic API {response.status_code}: {response.text}")

    raise RuntimeError(last_error or "Anthropic API request failed after retries")


def _parse_response(text, candidates):
    try:
        parsed = json.loads(text)
        return {item["ticker"]: item["analysis"] for item in parsed}
    except (json.JSONDecodeError, KeyError, TypeError):
        # Claude occasionally wraps JSON in prose despite instructions not to - fall back to
        # the raw text for every candidate rather than losing the whole run over a format slip.
        return {c["ticker"]: text for c in candidates}
