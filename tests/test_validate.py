import pandas as pd
import pytest

from klines.validate import (
    check_no_duplicates,
    check_no_gaps,
    check_ohlc_sanity,
    drop_partial_candle,
)
from conftest import make_h1_bars


def test_no_gaps_passes_on_clean_series():
    df = make_h1_bars("2023-01-01", 24)
    check_no_gaps(df)  # must not raise


def test_no_gaps_detects_missing_hour():
    df = make_h1_bars("2023-01-01", 24)
    df = df.drop(df.index[5])
    with pytest.raises(ValueError, match="gap"):
        check_no_gaps(df)


def test_no_duplicates_passes_on_clean_series():
    df = make_h1_bars("2023-01-01", 10)
    check_no_duplicates(df)  # must not raise


def test_no_duplicates_detects_repeated_timestamp():
    df = make_h1_bars("2023-01-01", 10)
    df = pd.concat([df, df.iloc[[3]]])
    with pytest.raises(ValueError, match="duplicate"):
        check_no_duplicates(df)


def test_ohlc_sanity_passes_on_clean_series():
    df = make_h1_bars("2023-01-01", 5)
    check_ohlc_sanity(df)  # must not raise


def test_ohlc_sanity_detects_high_below_low():
    df = make_h1_bars("2023-01-01", 5)
    df = df.copy()
    df.loc[df.index[2], "high"] = 50.0  # high < low (99)
    with pytest.raises(ValueError, match="OHLC"):
        check_ohlc_sanity(df)


def test_ohlc_sanity_detects_negative_volume():
    df = make_h1_bars("2023-01-01", 5)
    df = df.copy()
    df.loc[df.index[1], "volume"] = -1.0
    with pytest.raises(ValueError, match="OHLC"):
        check_ohlc_sanity(df)


def test_drop_partial_candle_removes_last_if_incomplete():
    df = make_h1_bars("2023-01-01", 10)
    # set now_utc to be within the last candle's period
    now = df.index[-1] + pd.Timedelta(minutes=30)
    result = drop_partial_candle(df, freq="1h", now_utc=now)
    assert len(result) == 9
    assert result.index[-1] == df.index[-2]


def test_drop_partial_candle_keeps_last_if_complete():
    df = make_h1_bars("2023-01-01", 10)
    # set now_utc to be after the last candle's period
    now = df.index[-1] + pd.Timedelta(hours=2)
    result = drop_partial_candle(df, freq="1h", now_utc=now)
    assert len(result) == 10
