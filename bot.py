import yfinance as yf
from datetime import datetime
import pytz

# ==========================
# NIFTY SYMBOL
# ==========================

SYMBOL = "^NSEI"

# ==========================
# DOWNLOAD DATA
# ==========================

def get_previous_day_ohlc():

    df = yf.download(
        SYMBOL,
        period="5d",
        interval="1d",
        progress=False,
        auto_adjust=False,
    )

    if len(df) < 2:
        raise Exception("Not enough data")

    prev = df.iloc[-2]

    return (
        float(prev["Open"]),
        float(prev["High"]),
        float(prev["Low"]),
        float(prev["Close"]),
    )

# ==========================
# WOODIE PIVOT
# ==========================

def woodie_pivot(open_, high, low, close):

    pivot = (high + low + 2 * close) / 4

    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high

    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)

    return {
        "Pivot": round(pivot, 2),
        "R1": round(r1, 2),
        "R2": round(r2, 2),
        "R3": round(r3, 2),
        "S1": round(s1, 2),
        "S2": round(s2, 2),
        "S3": round(s3, 2),
    }

# ==========================
# MAIN
# ==========================

def main():

    ist = pytz.timezone("Asia/Kolkata")

    print("=" * 50)
    print("ParthTraderAlerts - NIFTY Woodie Pivot
