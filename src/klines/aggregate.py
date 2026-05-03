import pandas as pd

_H4_ORIGIN = "2020-01-01"
_H4_ORIGIN_TS = pd.Timestamp(_H4_ORIGIN, tz="UTC")

_OHLCV_AGG: dict[str, str] = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
}

_H4_BARS = 4
_DAILY_BARS = 24
_WEEKLY_BARS = 6 * 24        # 144 H1 bars (≥ 86% of week, accepts 1-bar gaps)
_MONTHLY_BARS = 27 * 24      # 648 H1 bars (≥ 96% of shortest month, accepts 1-bar gaps)
_QUARTERLY_BARS = 87 * 24    # 2088 H1 bars (≥ 96.7% of shortest quarter, accepts gaps)


def _resample(
    h1: pd.DataFrame, rule: str, origin: str | pd.Timestamp, min_bars: int
) -> pd.DataFrame:
    resampled = h1.resample(rule, origin=origin, closed="left", label="left")
    counts = resampled["open"].count()
    agg = resampled.agg(_OHLCV_AGG)
    return agg[counts >= min_bars]


def aggregate_h4(h1: pd.DataFrame) -> pd.DataFrame:
    return _resample(h1, "4h", _H4_ORIGIN_TS, _H4_BARS)


def aggregate_daily(h1: pd.DataFrame) -> pd.DataFrame:
    return _resample(h1, "1D", "start_day", _DAILY_BARS)


def aggregate_weekly(h1: pd.DataFrame) -> pd.DataFrame:
    """Weekly bars, Monday 00:00 UTC open."""
    resampled = h1.resample("W-MON", closed="left", label="left")
    counts = resampled["open"].count()
    return resampled.agg(_OHLCV_AGG)[counts >= _WEEKLY_BARS]


def aggregate_monthly(h1: pd.DataFrame) -> pd.DataFrame:
    """Monthly bars, 1st of month 00:00 UTC open."""
    return _resample(h1, "MS", "start_day", _MONTHLY_BARS)


def aggregate_quarterly(h1: pd.DataFrame) -> pd.DataFrame:
    """Quarterly bars, Jan/Apr/Jul/Oct 1st 00:00 UTC open."""
    return _resample(h1, "QS", "start_day", _QUARTERLY_BARS)
