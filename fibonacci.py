def find_best_swing(closes):
    """Find the swing-low -> swing-high pair with the largest % rally, where the low
    strictly precedes the high (classic "buy low, sell high once" scan, O(n)).
    Returns (rally_pct, swing_low, low_idx, swing_high, high_idx), or None if prices
    never rose above their running minimum (e.g. a purely declining series)."""
    best = None
    running_min = closes[0]
    running_min_idx = 0
    for i, price in enumerate(closes):
        if price < running_min:
            running_min = price
            running_min_idx = i
            continue
        rally_pct = (price - running_min) / running_min * 100
        if best is None or rally_pct > best[0]:
            best = (rally_pct, running_min, running_min_idx, price, i)
    return best


def fib_level(swing_low, swing_high, ratio):
    return swing_high - (swing_high - swing_low) * ratio


if __name__ == "__main__":
    # A rally from 100 to 200: 61.8% retracement = 138.2, 65% retracement = 135.0
    # (the "golden pocket" band is 135.0-138.2 - higher retracement % means a deeper
    # pullback, i.e. a LOWER price, so fib65 < fib618).
    print(fib_level(100, 200, 0.618))
    print(fib_level(100, 200, 0.65))

    swing = find_best_swing([50, 40, 100, 90, 70, 80])
    print(swing)  # expect rally from 40 (idx 1) to 100 (idx 2)
