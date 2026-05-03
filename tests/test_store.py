import pandas as pd

from klines.store import load_parquet, save_parquet
from conftest import make_h1_bars


def test_round_trip_preserves_index_and_dtypes(tmp_path):
    df = make_h1_bars("2023-01-01", 24)
    path = tmp_path / "test.parquet"

    save_parquet(df, path)
    loaded = load_parquet(path)

    assert loaded.index.dtype == df.index.dtype
    assert str(loaded.index.tz) == "UTC"
    assert list(loaded.columns) == list(df.columns)
    assert (loaded.dtypes == df.dtypes).all()
    pd.testing.assert_frame_equal(loaded, df, check_freq=False)


def test_save_creates_parent_directories(tmp_path):
    df = make_h1_bars("2023-01-01", 4)
    path = tmp_path / "nested" / "dir" / "data.parquet"

    save_parquet(df, path)

    assert path.exists()


def test_load_preserves_utc_timezone(tmp_path):
    df = make_h1_bars("2023-06-15", 10)
    path = tmp_path / "tz_test.parquet"

    save_parquet(df, path)
    loaded = load_parquet(path)

    assert loaded.index.tzinfo is not None
    assert str(loaded.index.tz) == "UTC"
