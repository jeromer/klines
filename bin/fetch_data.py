#!/usr/bin/env python3
"""Download raw klines from Binance and store as Parquet."""

import argparse
import asyncio
import datetime
import os
from pathlib import Path

import pandas as pd

from klines.download import FUTURES_URL, SPOT_URL, KlineRequest, ProgressCallback, fetch_all
from klines.normalise import normalise_klines
from klines.store import load_parquet, save_parquet

_INTERVAL_MAP: dict[str, tuple[str, str]] = {
    "m15": ("15m", "M15"),
    "h1":  ("1h",  "H1"),
    "h4":  ("4h",  "H4"),
    "d":   ("1d",  "D1"),
}

_MARKET_URL: dict[str, str] = {
    "spot":    SPOT_URL,
    "futures": FUTURES_URL,
}


def _parse_args(defaults: dict) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Binance klines")
    parser.add_argument(
        "--market",
        choices=list(_MARKET_URL),
        default="spot",
        help="market to download from (default: spot)",
    )
    parser.add_argument(
        "--interval",
        choices=list(_INTERVAL_MAP),
        default="h1",
        help="candle interval to download (default: h1)",
    )
    parser.add_argument(
        "--symbols",
        type=lambda s: s.split(","),
        default=defaults.get("symbols"),
        metavar="SYMBOL[,SYMBOL...]",
        help="comma-separated symbols to download",
    )
    parser.add_argument(
        "--start",
        default=defaults.get("start", "2017-01-01"),
        metavar="YYYY-MM-DD",
        help="start date in UTC (default: 2017-01-01)",
    )
    parser.add_argument(
        "--end",
        default=datetime.date.today().isoformat(),
        metavar="YYYY-MM-DD",
        help="end date in UTC (default: today)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(defaults.get("output_dir", "./data/raw")),
        metavar="DIR",
        help="directory for output Parquet files (default: ./data/raw)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        metavar="N",
        help="max concurrent HTTP workers (default: CPU core count)",
    )
    parser.add_argument(
        "--progress",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="show download progress (default: enabled)",
    )
    args = parser.parse_args()
    if args.symbols is None:
        parser.error("--symbols is required (e.g. --symbols BTCUSDT,ETHUSDT)")
    return args


def _make_progress_callback() -> ProgressCallback:
    def on_progress(symbol: str, done: int, total: int) -> None:
        print(f"\r{symbol}: {done}/{total} batches", end="", flush=True)
        if done == total:
            print()

    return on_progress


def _resume_start_ms(path: Path, default_start: str) -> int:
    if path.exists():
        existing = load_parquet(path)
        if not existing.empty:
            return int(existing.index[-1].timestamp() * 1000) + 1
    return int(pd.Timestamp(default_start, tz="UTC").timestamp() * 1000)


async def _run(args: argparse.Namespace) -> None:
    binance_interval, filename_suffix = _INTERVAL_MAP[args.interval]
    url = _MARKET_URL[args.market]
    end_ms = int(pd.Timestamp(args.end, tz="UTC").timestamp() * 1000)

    requests = []
    for symbol in args.symbols:
        path = args.output_dir / f"{symbol}_{filename_suffix}.parquet"
        start_ms = _resume_start_ms(path, args.start)
        if start_ms >= end_ms:
            print(f"{symbol}: already up to date")
            continue
        requests.append(
            KlineRequest(symbol=symbol, interval=binance_interval, start_ms=start_ms, end_ms=end_ms, url=url)
        )

    if not requests:
        return

    on_progress = _make_progress_callback() if args.progress else None
    print(f"Downloading {len(requests)} symbol(s) [{args.market}/{args.interval}] with up to {args.workers} concurrent workers...")
    raw_by_symbol = await fetch_all(requests, max_workers=args.workers, on_progress=on_progress)

    for symbol, raw_df in raw_by_symbol.items():
        new_df = normalise_klines(raw_df)
        path = args.output_dir / f"{symbol}_{filename_suffix}.parquet"
        if path.exists():
            existing = load_parquet(path)
            new_df = pd.concat([existing, new_df]).sort_index()
            new_df = new_df[~new_df.index.duplicated(keep="last")]
        save_parquet(new_df, path)
        print(f"{symbol}: {len(new_df)} candles total → {path}")


def main(defaults: dict | None = None) -> None:
    args = _parse_args(defaults or {})
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
