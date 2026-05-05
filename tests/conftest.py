import pandas as pd


def make_h1_bars(start: str, periods: int) -> pd.DataFrame:
    index = pd.date_range(start, periods=periods, freq="1h", tz="UTC")
    return pd.DataFrame(
        {
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000.0,
        },
        index=index,
    )


def make_m15_bars(start: str, periods: int) -> pd.DataFrame:
    index = pd.date_range(start, periods=periods, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000.0,
        },
        index=index,
    )
