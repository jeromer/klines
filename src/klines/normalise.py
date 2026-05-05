import logging

import pandas as pd

# Binance spot kline timestamps switched from milliseconds to microseconds
# for data from 2025-01-01 00:00:00 UTC onwards.
_US_THRESHOLD: int = 1_735_689_600_000_000

_RAW_COLUMNS: list[str] = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trade_count",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]

_OUTPUT_COLUMNS: list[str] = ["open", "high", "low", "close", "volume"]

logger = logging.getLogger(__name__)


def normalise_klines(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = _RAW_COLUMNS

    open_time = df["open_time"].astype("int64")
    ts_ms = open_time.where(open_time <= _US_THRESHOLD, open_time // 1000)
    index = pd.to_datetime(ts_ms, unit="ms", utc=True)

    result = df[_OUTPUT_COLUMNS].astype("float64")
    result.index = index
    result.index.name = None

    dupes = result.index.duplicated().sum()
    if dupes > 0:
        logger.warning("%d duplicate timestamp(s) dropped from Binance data", dupes)
        result = result[~result.index.duplicated(keep="last")]

    return result
