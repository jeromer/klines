import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from klines.pipeline import FetchConfig, fetch


def _make_config(end: str, tmp_path: Path) -> FetchConfig:
    return FetchConfig(
        symbols=["BTCUSDT"],
        url="https://example.com",
        interval="1h",
        filename_suffix="H1",
        start="2026-05-13",
        end=end,
        output_dir=tmp_path,
        workers=1,
        progress=False,
    )


def test_end_ms_covers_full_end_date(tmp_path):
    """end_ms must be midnight of end+1 so bars opened on end date are included."""
    captured: list[int] = []

    async def fake_fetch_all(requests, *, max_workers, on_progress):
        captured.extend(r.end_ms for r in requests)
        return {}

    config = _make_config("2026-05-13", tmp_path)
    with patch("klines.pipeline.fetch_all", side_effect=fake_fetch_all):
        asyncio.run(fetch(config))

    assert len(captured) == 1
    expected_ms = int(pd.Timestamp("2026-05-14", tz="UTC").timestamp() * 1000)
    assert captured[0] == expected_ms


def test_end_ms_old_behaviour_would_exclude_end_date_bars():
    """Regression: midnight of end date (old behaviour) excludes all same-day bars."""
    midnight_today_ms = int(pd.Timestamp("2026-05-13", tz="UTC").timestamp() * 1000)
    first_bar_today_ms = int(pd.Timestamp("2026-05-13 00:00:00", tz="UTC").timestamp() * 1000)
    # bar opens at midnight — old code excluded it because openTime >= end_ms
    assert first_bar_today_ms >= midnight_today_ms


def test_end_ms_new_behaviour_includes_end_date_bars():
    """New end_ms (midnight of end+1) includes bars opened anywhere on end date."""
    end_ms = int((pd.Timestamp("2026-05-13", tz="UTC") + pd.Timedelta(days=1)).timestamp() * 1000)
    last_bar_today_ms = int(pd.Timestamp("2026-05-13 23:00:00", tz="UTC").timestamp() * 1000)
    assert last_bar_today_ms < end_ms
