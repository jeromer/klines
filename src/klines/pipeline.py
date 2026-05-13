import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from klines.aggregate import (
    aggregate_daily,
    aggregate_h1,
    aggregate_h4,
    aggregate_monthly,
    aggregate_quarterly,
    aggregate_weekly,
)
from klines.download import KlineRequest, ProgressCallback, fetch_all
from klines.normalise import normalise_klines
from klines.store import load_parquet, save_parquet
from klines.validate import validate_h1, validate_m15

logger = logging.getLogger(__name__)

_TIMEFRAMES: list[tuple[str, Callable[[pd.DataFrame], pd.DataFrame]]] = [
    ("H4", aggregate_h4),
    ("D1", aggregate_daily),
    ("W1", aggregate_weekly),
    ("M1", aggregate_monthly),
    ("Q1", aggregate_quarterly),
]


@dataclass(frozen=True)
class _SourceSpec:
    suffix: str
    validate_fn: Callable[[pd.DataFrame], pd.DataFrame]
    to_h1: Callable[[pd.DataFrame], pd.DataFrame] | None  # None = input is already H1


_SPECS: dict[str, _SourceSpec] = {
    "h1": _SourceSpec("H1", validate_h1, None),
    "m15": _SourceSpec("M15", validate_m15, aggregate_h1),
}


@dataclass(frozen=True)
class FetchConfig:
    symbols: list[str]
    url: str
    interval: str
    filename_suffix: str
    start: str
    end: str
    output_dir: Path
    workers: int
    progress: bool = True


def _resume_start_ms(path: Path, default_start: str) -> int:
    if path.exists():
        existing = load_parquet(path)
        if not existing.empty:
            return int(existing.index[-1].timestamp() * 1000) + 1
    return int(pd.Timestamp(default_start, tz="UTC").timestamp() * 1000)


def _make_progress_callback() -> ProgressCallback:
    def on_progress(symbol: str, done: int, total: int) -> None:
        if done == total:
            logger.info("%s: %d/%d batches downloaded", symbol, done, total)
        else:
            logger.debug("%s: %d/%d batches", symbol, done, total)

    return on_progress


async def fetch(config: FetchConfig) -> None:
    end_ms = int((pd.Timestamp(config.end, tz="UTC") + pd.Timedelta(days=1)).timestamp() * 1000)

    requests = []
    for symbol in config.symbols:
        path = config.output_dir / f"{symbol}_{config.filename_suffix}.parquet"
        start_ms = _resume_start_ms(path, config.start)
        if start_ms >= end_ms:
            logger.info("%s: already up to date", symbol)
            continue
        requests.append(
            KlineRequest(
                symbol=symbol,
                interval=config.interval,
                start_ms=start_ms,
                end_ms=end_ms,
                url=config.url,
            )
        )

    if not requests:
        return

    on_progress = _make_progress_callback() if config.progress else None
    logger.info(
        "Downloading %d symbol(s) with up to %d concurrent workers...",
        len(requests),
        config.workers,
    )
    raw_by_symbol = await fetch_all(requests, max_workers=config.workers, on_progress=on_progress)

    for symbol, raw_df in raw_by_symbol.items():
        new_df = normalise_klines(raw_df)
        path = config.output_dir / f"{symbol}_{config.filename_suffix}.parquet"
        if path.exists():
            existing = load_parquet(path)
            new_df = pd.concat([existing, new_df]).sort_index()
            new_df = new_df[~new_df.index.duplicated(keep="last")]
        save_parquet(new_df, path)
        logger.info("%s: %d candles total -> %s", symbol, len(new_df), path)


def build(symbols: list[str], raw_dir: Path, output_dir: Path, source: str = "h1") -> None:
    spec = _SPECS[source]
    for symbol in symbols:
        raw = spec.validate_fn(load_parquet(raw_dir / f"{symbol}_{spec.suffix}.parquet"))
        h1 = spec.to_h1(raw) if spec.to_h1 else raw
        outputs: list[tuple[str, pd.DataFrame]] = [("H1", h1)] + [
            (label, fn(h1)) for label, fn in _TIMEFRAMES
        ]
        for label, df in outputs:
            path = output_dir / f"{symbol}_{label}.parquet"
            save_parquet(df, path)
            logger.info("%s: %s=%d candles -> %s", symbol, label, len(df), path)
