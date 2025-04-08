# my_kite_ticker.py

import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta

class MyKiteTicker:
    """
    Mimics yfinance.Ticker but uses:
    - Kite Connect for price history
    - A user-provided dict (from Screener or similar) for fundamentals
    """

    def __init__(self, symbol, kite, instrument_df, info_dict=None):
        # If symbol ends with ".NS", remove that for token lookup
        if symbol.endswith(".NS"):
            symbol = symbol.replace(".NS", "")  # "RELIANCE.NS" -> "RELIANCE"

        self.symbol = symbol
        self.kite = kite
        self.instrument_df = instrument_df

        # If user gave fundamentals, store them; else dummy
        self._info = info_dict or {
            "longName": "Unknown Company",
            "shortName": self.symbol,
            "longBusinessSummary": "No summary provided",
            "symbol": self.symbol
        }

    def __repr__(self):
        """Mimic yfinance.Ticker's representation."""
        return f"<MyKiteTicker object {self.symbol}>"

    @property
    def info(self):
        """
        Mimics yfinance's 'stock.info' property.

        Instead of Yahoo data, returns your user-provided or scraped fundamentals.
        """
        return self._info

    def history(self, period=None, interval="1d", start=None, end=None):
        """
        Mimics yfinance's 'stock.history()' method.

        Parameters
        ----------
        period : str (like '1y', '6mo', '7d')
        interval : str (like '1d', '5m', '15m')
        start, end : datetime or str (optional)

        Returns
        -------
        pd.DataFrame
            Columns: ['Open','High','Low','Close','Volume'], indexed by DatetimeIndex
        """
        #Convert yfinance intervals to Kite intervals
        interval_map ={
            "1d": "day",
            "1m": "minute",
            "5m": "5minute",
            "15m": "15minute",
            "30m": "30minute",
            "60m": "60minute",
        }
        kite_interval = interval_map.get(interval, "day")

        if start is None and end is None and period is not None:
            # No explicit start/end => parse 'period'
            now = datetime.datetime.now()
            from_date, to_date = self._parse_period(period, now)
        else:
            # If user gave start/end, use them; else fallback to last 1 year
            if start is not None:
                from_date = pd.to_datetime(start)
            else:
                from_date = datetime.datetime.now() - relativedelta(years=1)

            if end is not None:
                to_date = pd.to_datetime(end)
            else:
                to_date = datetime.datetime.now()

        # Get the instrument token from instrument_df
        df_filtered = self.instrument_df[
            (self.instrument_df["tradingsymbol"] == self.symbol) &
            (self.instrument_df["exchange"] == "NSE")
        ]
        if df_filtered.empty:
            raise ValueError(f"No instrument token found for {self.symbol} on NSE!")

        instrument_token = df_filtered["instrument_token"].values[0]

        # Fetch historical data from Kite
        data = self.kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval=kite_interval
        )
        df = pd.DataFrame(data)
        if df.empty:
            return df  # Return empty if no data found

        # Rename columns to mimic yfinance
        df.rename(columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }, inplace=True)

        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        return df

    def _parse_period(self, period, now):
        """Helper: convert '1y', '6mo', etc. to a (from_date, to_date) tuple."""
        period = period.lower()
        to_date = now

        if period.endswith("y"):  # e.g. "1y"
            years = int(period[:-1])
            from_date = now - relativedelta(years=years)
        elif period.endswith("mo"):  # e.g. "6mo"
            months = int(period[:-2])
            from_date = now - relativedelta(months=months)
        elif period.endswith("d"):  # e.g. "7d"
            days = int(period[:-1])
            from_date = now - datetime.timedelta(days=days)
        else:
            # Default to 1 year if unrecognized format
            from_date = now - relativedelta(years=1)

        return (from_date, to_date)
