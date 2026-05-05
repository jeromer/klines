#!/usr/bin/env python3
"""Download raw klines from Binance and store as Parquet."""

import argparse
import asyncio
import datetime
import logging
import os
from pathlib import Path

from klines.download import FUTURES_URL, SPOT_URL
from klines.pipeline import FetchConfig, fetch

_INTERVAL_MAP: dict[str, tuple[str, str]] = {
    "m15": ("15m", "M15"),
    "h1": ("1h", "H1"),
    "h4": ("4h", "H4"),
    "d": ("1d", "D1"),
}

_MARKET_URL: dict[str, str] = {
    "spot": SPOT_URL,
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


def main(defaults: dict | None = None) -> None:
    args = _parse_args(defaults or {})
    binance_interval, filename_suffix = _INTERVAL_MAP[args.interval]
    asyncio.run(
        fetch(
            FetchConfig(
                symbols=args.symbols,
                url=_MARKET_URL[args.market],
                interval=binance_interval,
                filename_suffix=filename_suffix,
                start=args.start,
                end=args.end,
                output_dir=args.output_dir,
                workers=args.workers,
                progress=args.progress,
            )
        )
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
