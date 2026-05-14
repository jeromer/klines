import logging

import pandas as pd

logger = logging.getLogger(__name__)


def check_no_gaps(df: pd.DataFrame, freq: str = "1h") -> None:
    if df.empty:
        return
    expected = pd.date_range(df.index[0], df.index[-1], freq=freq, tz="UTC")
    missing = expected.difference(df.index)
    if len(missing) > 0:
        raise ValueError(
            f"{len(missing)} gap(s) found in {freq} series. First missing: {missing[:3].tolist()}"
        )


def fill_gaps(df: pd.DataFrame, freq: str = "1h") -> pd.DataFrame:
    if df.empty:
        return df
    expected = pd.date_range(df.index[0], df.index[-1], freq=freq, tz="UTC")
    missing_count = len(expected.difference(df.index))
    if missing_count == 0:
        return df
    logger.warning("%d gap(s) forward-filled with zero-volume candles", missing_count)
    df = df.reindex(expected)
    df["close"] = df["close"].ffill()
    df[["open", "high", "low"]] = df[["open", "high", "low"]].fillna(df["close"])
    df["volume"] = df["volume"].fillna(0.0)
    return df


def check_no_duplicates(df: pd.DataFrame) -> None:
    dupes = df.index[df.index.duplicated()]
    if len(dupes) > 0:
        raise ValueError(
            f"{len(dupes)} duplicate timestamp(s) found. First duplicates: {dupes[:3].tolist()}"
        )


def check_ohlc_sanity(df: pd.DataFrame) -> None:
    violations = (
        (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["high"] < df["low"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
        | (df["volume"] < 0)
    )
    count = violations.sum()
    if count > 0:
        raise ValueError(
            f"{count} OHLC sanity violation(s) found. Sample rows:\n{df[violations].head(3)}"
        )


def drop_partial_candle(df: pd.DataFrame, freq: str, now_utc: pd.Timestamp) -> pd.DataFrame:
    if df.empty:
        return df
    last_ts = df.index[-1]
    candle_end = last_ts + pd.tseries.frequencies.to_offset(freq)
    if candle_end > now_utc:
        return df.iloc[:-1]
    return df


def validate_h1(df: pd.DataFrame) -> pd.DataFrame:
    dupes = df.index.duplicated().sum()
    if dupes > 0:
        logger.warning("%d duplicate timestamp(s) dropped", dupes)
        df = df[~df.index.duplicated(keep="last")]
    df = fill_gaps(df, freq="1h")
    check_no_gaps(df, freq="1h")
    check_ohlc_sanity(df)
    return drop_partial_candle(df, freq="1h", now_utc=pd.Timestamp.now(tz="UTC"))


def validate_m15(df: pd.DataFrame) -> pd.DataFrame:
    dupes = df.index.duplicated().sum()
    if dupes > 0:
        logger.warning("%d duplicate timestamp(s) dropped", dupes)
        df = df[~df.index.duplicated(keep="last")]
    df = fill_gaps(df, freq="15min")
    check_no_gaps(df, freq="15min")
    check_ohlc_sanity(df)
    return drop_partial_candle(df, freq="15min", now_utc=pd.Timestamp.now(tz="UTC"))
