def rsi(closes, period=14):
    valid_closes = [c for c in closes if c is not None]
    deltas = [valid_closes[i] - valid_closes[i - 1] for i in range(1, len(valid_closes))]
    recent = deltas[-period:]

    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


if __name__ == "__main__":
    # Steadily rising closes -> no losses -> RSI should be 100.
    print(rsi([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], period=14))
    # Steadily falling closes -> no gains -> RSI should be 0.
    print(rsi([15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1], period=14))
