import pandas as pd

from klines.aggregate import (
    aggregate_daily,
    aggregate_h4,
    aggregate_monthly,
    aggregate_quarterly,
    aggregate_weekly,
)
from conftest import make_h1_bars


def test_h4_boundary_anchoring():
    df = make_h1_bars("2023-01-01 00:00", 24)
    result = aggregate_h4(df)

    assert len(result) == 6
    assert list(result.index.hour) == [0, 4, 8, 12, 16, 20]


def test_h4_boundaries_are_utc():
    df = make_h1_bars("2023-01-01 00:00", 24)
    result = aggregate_h4(df)

    assert str(result.index.tz) == "UTC"


def test_h4_ohlcv_aggregation():
    # build 4 bars with distinct values to verify each aggregation function
    index = pd.date_range("2023-01-01 00:00", periods=4, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [10.0, 20.0, 30.0, 40.0],
            "high": [15.0, 25.0, 35.0, 45.0],
            "low": [8.0, 18.0, 28.0, 38.0],
            "close": [12.0, 22.0, 32.0, 42.0],
            "volume": [100.0, 200.0, 300.0, 400.0],
        },
        index=index,
    )
    result = aggregate_h4(df)

    assert result.iloc[0]["open"] == 10.0
    assert result.iloc[0]["high"] == 45.0
    assert result.iloc[0]["low"] == 8.0
    assert result.iloc[0]["close"] == 42.0
    assert result.iloc[0]["volume"] == 1000.0


def test_h4_drops_partial_tail_group():
    # 27 bars = 6 complete H4 groups + 3 orphan bars
    df = make_h1_bars("2023-01-01 00:00", 27)
    result = aggregate_h4(df)

    assert len(result) == 6
    assert list(result.index.hour) == [0, 4, 8, 12, 16, 20]


def test_h4_multi_day_continuity():
    df = make_h1_bars("2023-01-01 00:00", 48)
    result = aggregate_h4(df)

    assert len(result) == 12


def test_daily_boundary_at_midnight_utc():
    df = make_h1_bars("2023-01-01 00:00", 24)
    result = aggregate_daily(df)

    assert len(result) == 1
    assert result.index[0] == pd.Timestamp("2023-01-01 00:00:00", tz="UTC")


def test_daily_ohlcv_aggregation():
    index = pd.date_range("2023-01-01 00:00", periods=24, freq="1h", tz="UTC")
    opens = [float(i) for i in range(24)]
    highs = [float(i + 5) for i in range(24)]
    lows = [float(i - 1) for i in range(24)]
    closes = [float(i + 1) for i in range(24)]
    volumes = [100.0] * 24

    df = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=index,
    )
    result = aggregate_daily(df)

    assert result.iloc[0]["open"] == 0.0
    assert result.iloc[0]["high"] == 28.0
    assert result.iloc[0]["low"] == -1.0
    assert result.iloc[0]["close"] == 24.0
    assert result.iloc[0]["volume"] == 2400.0


def test_daily_drops_partial_tail_group():
    # 25 bars = 1 complete day + 1 orphan bar
    df = make_h1_bars("2023-01-01 00:00", 25)
    result = aggregate_daily(df)

    assert len(result) == 1


def test_daily_multi_day_continuity():
    df = make_h1_bars("2023-01-01 00:00", 48)
    result = aggregate_daily(df)

    assert len(result) == 2
    assert result.index[0] == pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    assert result.index[1] == pd.Timestamp("2023-01-02 00:00:00", tz="UTC")


# ---------------------------------------------------------------------------
# Weekly
# ---------------------------------------------------------------------------


def test_weekly_opens_on_monday():
    # 2023-01-02 is a Monday — one full week = 168 H1 bars
    df = make_h1_bars("2023-01-02 00:00", 7 * 24)
    result = aggregate_weekly(df)

    assert len(result) == 1
    assert result.index[0].day_of_week == 0  # Monday
    assert result.index[0] == pd.Timestamp("2023-01-02 00:00:00", tz="UTC")


def test_weekly_drops_partial_tail():
    # 1.5 weeks: 1 complete + 84 orphan H1 bars (< 168 threshold)
    df = make_h1_bars("2023-01-02 00:00", 7 * 24 + 84)
    result = aggregate_weekly(df)

    assert len(result) == 1


def test_weekly_two_complete_weeks():
    df = make_h1_bars("2023-01-02 00:00", 14 * 24)
    result = aggregate_weekly(df)

    assert len(result) == 2
    assert result.index[0] == pd.Timestamp("2023-01-02 00:00:00", tz="UTC")
    assert result.index[1] == pd.Timestamp("2023-01-09 00:00:00", tz="UTC")


def test_weekly_ohlcv_aggregation():
    # 7 * 24 bars: open of first, close of last, max high, min low, sum volume
    df = make_h1_bars("2023-01-02 00:00", 7 * 24)
    result = aggregate_weekly(df)

    assert result.iloc[0]["open"] == 100.0
    assert result.iloc[0]["high"] == 102.0
    assert result.iloc[0]["low"] == 99.0
    assert result.iloc[0]["close"] == 101.0
    assert result.iloc[0]["volume"] == 7 * 24 * 1000.0


# ---------------------------------------------------------------------------
# Monthly
# ---------------------------------------------------------------------------


def test_monthly_opens_on_first_of_month():
    # January 2023 = 31 days = 744 H1 bars
    df = make_h1_bars("2023-01-01 00:00", 31 * 24)
    result = aggregate_monthly(df)

    assert len(result) == 1
    assert result.index[0] == pd.Timestamp("2023-01-01 00:00:00", tz="UTC")


def test_monthly_drops_partial_tail():
    # January (744 bars) + 10 orphan H1 bars into February
    df = make_h1_bars("2023-01-01 00:00", 31 * 24 + 10)
    result = aggregate_monthly(df)

    assert len(result) == 1


def test_monthly_two_complete_months():
    # January (744) + February non-leap (672)
    df = make_h1_bars("2023-01-01 00:00", (31 + 28) * 24)
    result = aggregate_monthly(df)

    assert len(result) == 2
    assert result.index[0] == pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    assert result.index[1] == pd.Timestamp("2023-02-01 00:00:00", tz="UTC")


# ---------------------------------------------------------------------------
# Quarterly
# ---------------------------------------------------------------------------


def test_quarterly_opens_on_quarter_start():
    # Q1 2023: Jan + Feb + Mar = 31+28+31 = 90 days = 2160 H1 bars
    df = make_h1_bars("2023-01-01 00:00", 90 * 24)
    result = aggregate_quarterly(df)

    assert len(result) == 1
    assert result.index[0] == pd.Timestamp("2023-01-01 00:00:00", tz="UTC")


def test_quarterly_drops_partial_tail():
    # Q1 2023 (2160 bars) + 10 orphan H1 bars into Q2
    df = make_h1_bars("2023-01-01 00:00", 90 * 24 + 10)
    result = aggregate_quarterly(df)

    assert len(result) == 1


def test_quarterly_two_complete_quarters():
    # Q1 (90 days) + Q2 (91 days) 2023
    df = make_h1_bars("2023-01-01 00:00", (90 + 91) * 24)
    result = aggregate_quarterly(df)

    assert len(result) == 2
    assert result.index[0] == pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    assert result.index[1] == pd.Timestamp("2023-04-01 00:00:00", tz="UTC")
