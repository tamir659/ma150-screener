def sma(closes, window):
    valid_closes = [c for c in closes if c is not None]
    last_n = valid_closes[-window:]
    return sum(last_n) / len(last_n)


def pct_distance(price, average):
    return (price - average) / average * 100


if __name__ == "__main__":
    test_result = sma([1, 2, 3, 4, 5], 5)
    print(test_result)

    test_result2 = pct_distance(110, 100)
    print(test_result2)
