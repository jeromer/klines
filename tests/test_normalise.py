import pandas as pd

from klines.normalise import normalise_klines

_OHLCV = ["open", "high", "low", "close", "volume"]


def _make_raw(open_times: list[int]) -> pd.DataFrame:
    n = len(open_times)
    return pd.DataFrame(
        {
            0: open_times,
            1: [100.0] * n,
            2: [102.0] * n,
            3: [99.0] * n,
            4: [101.0] * n,
            5: [1000.0] * n,
            6: [0] * n,
            7: [0] * n,
            8: [0] * n,
            9: [0] * n,
            10: [0] * n,
            11: [0] * n,
        }
    )


# 2023-01-01 00:00:00 UTC in milliseconds
_MS_2023 = 1_672_531_200_000
# 2025-02-01 00:00:00 UTC in microseconds
_US_2025 = 1_738_368_000_000_000


def test_pre_2025_ms_timestamps():
    raw = _make_raw([_MS_2023, _MS_2023 + 3_600_000])
    result = normalise_klines(raw)

    assert str(result.index[0]) == "2023-01-01 00:00:00+00:00"
    assert str(result.index[1]) == "2023-01-01 01:00:00+00:00"


def test_post_2025_us_timestamps():
    raw = _make_raw([_US_2025, _US_2025 + 3_600_000_000])
    result = normalise_klines(raw)

    assert str(result.index[0]) == "2025-02-01 00:00:00+00:00"
    assert str(result.index[1]) == "2025-02-01 01:00:00+00:00"


def test_mixed_batch_spanning_2025_boundary():
    # last ms timestamp before threshold, first us timestamp after
    ms_late = 1_735_689_600_000  # 2025-01-01 00:00:00 UTC in ms
    us_early = 1_735_693_200_000_000  # 2025-01-01 01:00:00 UTC in us
    raw = _make_raw([ms_late, us_early])
    result = normalise_klines(raw)

    assert str(result.index[0]) == "2025-01-01 00:00:00+00:00"
    assert str(result.index[1]) == "2025-01-01 01:00:00+00:00"


def test_output_has_exactly_five_columns():
    raw = _make_raw([_MS_2023])
    result = normalise_klines(raw)

    assert list(result.columns) == _OHLCV


def test_index_is_utc_datetime():
    raw = _make_raw([_MS_2023])
    result = normalise_klines(raw)

    assert isinstance(result.index, pd.DatetimeIndex)
    assert str(result.index.tz) == "UTC"


def test_all_columns_are_float64():
    raw = _make_raw([_MS_2023])
    result = normalise_klines(raw)

    assert (result.dtypes == "float64").all()
