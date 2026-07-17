# ==========================================================
# ParthTraderAlerts Telegram Pivot Bot
# data.py
# Yahoo Finance Market Data
# ==========================================================

import logging
import time
from datetime import datetime

import pandas as pd
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


class YahooMarketData:

    def __init__(self, retries=3, delay=2):
        self.retries = retries
        self.delay = delay

    def fetch_previous_day_ohlc(self, symbol):
        """
        Fetch Previous Trading Day OHLC
        """

        for attempt in range(self.retries):

            try:

                ticker = yf.Ticker(symbol)

                df = ticker.history(
                    period="7d",
                    interval="1d",
                    auto_adjust=False
                )

                if df.empty:
                    raise Exception("No market data received.")

                df = df.dropna()

                if len(df) < 2:
                    raise Exception("Not enough candles.")

                previous = df.iloc[-1]

                data = {
                    "High": round(float(previous["High"]), 2),
                    "Low": round(float(previous["Low"]), 2),
                    "Close": round(float(previous["Close"]), 2),
                    "Date": str(previous.name.date())
                }

                logging.info(f"{symbol} Previous OHLC Loaded")

                return data

            except Exception as e:

                logging.warning(
                    f"{symbol} Attempt {attempt+1} Failed : {e}"
                )

                time.sleep(self.delay)

        logging.error(f"{symbol} Data Fetch Failed")

        return None

    def fetch_live_price(self, symbol):
        """
        Fetch Latest Market Price
        """

        for attempt in range(self.retries):

            try:

                ticker = yf.Ticker(symbol)

                df = ticker.history(
                    period="1d",
                    interval="1m"
                )

                if df.empty:
                    raise Exception("Live data unavailable.")

                price = round(float(df["Close"].iloc[-1]), 2)

                return price

            except Exception as e:

                logging.warning(
                    f"{symbol} Live Price Error : {e}"
                )

                time.sleep(self.delay)

        return None

    def market_bias(self, live_price, pivot):

        if live_price is None:
            return "Unknown"

        if live_price > pivot:
            return "Bullish"

        if live_price < pivot:
            return "Bearish"

        return "Neutral"

    def get_complete_data(self, symbol):

        previous = self.fetch_previous_day_ohlc(symbol)

        if previous is None:
            return None

        live_price = self.fetch_live_price(symbol)

        return {
            "symbol": symbol,
            "date": previous["Date"],
            "high": previous["High"],
            "low": previous["Low"],
            "close": previous["Close"],
            "live_price": live_price
        }
# ==========================================================
# Additional Helper Functions
# ==========================================================

from config import SYMBOLS
from pivot import calculate_pivot, calculate_cpr


def get_all_market_data():
    """
    Fetch data for all configured symbols
    """

    market = YahooMarketData()

    results = {}

    for name, symbol in SYMBOLS.items():

        try:

            data = market.get_complete_data(symbol)

            if data is None:
                continue

            pivot = calculate_pivot(
                data["high"],
                data["low"],
                data["close"]
            )

            cpr = calculate_cpr(
                data["high"],
                data["low"],
                data["close"]
            )

            bias = market.market_bias(
                data["live_price"],
                pivot["Pivot"]
            )

            results[name] = {
                "symbol": symbol,
                "date": data["date"],
                "high": data["high"],
                "low": data["low"],
                "close": data["close"],
                "live_price": data["live_price"],
                "pivot": pivot,
                "cpr": cpr,
                "bias": bias
            }

        except Exception as e:

            logging.error(f"{name} : {e}")

    return results


# ==========================================================
# Testing
# ==========================================================

if __name__ == "__main__":

    data = get_all_market_data()

    print("=" * 60)

    for index_name, value in data.items():

        print(index_name)

        print("Date :", value["date"])
        print("Live :", value["live_price"])

        print("High :", value["high"])
        print("Low :", value["low"])
        print("Close :", value["close"])

        print()

        print("Pivot :", value["pivot"]["Pivot"])

        print("R1 :", value["pivot"]["R1"])
        print("R2 :", value["pivot"]["R2"])
        print("R3 :", value["pivot"]["R3"])

        print("S1 :", value["pivot"]["S1"])
        print("S2 :", value["pivot"]["S2"])
        print("S3 :", value["pivot"]["S3"])

        print()

        print("CPR")

        print("TC :", value["cpr"]["TC"])
        print("Pivot :", value["cpr"]["Pivot"])
        print("BC :", value["cpr"]["BC"])

        print()

        print("Bias :", value["bias"])

        print("=" * 60)
