# ==========================================
# Pivot Calculation
# ==========================================

def calculate_pivot(high, low, close):

    pivot = round((high + low + close) / 3, 2)

    r1 = round((2 * pivot) - low, 2)
    s1 = round((2 * pivot) - high, 2)

    r2 = round(pivot + (high - low), 2)
    s2 = round(pivot - (high - low), 2)

    r3 = round(high + 2 * (pivot - low), 2)
    s3 = round(low - 2 * (high - pivot), 2)

    return {
        "Pivot": pivot,
        "R1": r1,
        "R2": r2,
        "R3": r3,
        "S1": s1,
        "S2": s2,
        "S3": s3
    }


def calculate_cpr(high, low, close):

    pivot = (high + low + close) / 3

    bc = (high + low) / 2

    tc = (pivot - bc) + pivot

    return {
        "Pivot": round(pivot, 2),
        "BC": round(min(tc, bc), 2),
        "TC": round(max(tc, bc), 2)
    }


def market_bias(price, pivot):

    if price > pivot:
        return "Bullish"

    elif price < pivot:
        return "Bearish"

    return "Neutral"
