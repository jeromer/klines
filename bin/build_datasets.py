#!/usr/bin/env python3
"""Validate raw H1 data and build H4/D1/W1/M1/Q1 processed datasets."""

import argparse
from pathlib import Path

from klines.aggregate import (
    aggregate_daily,
    aggregate_h4,
    aggregate_monthly,
    aggregate_quarterly,
    aggregate_weekly,
)
from klines.store import load_parquet, save_parquet
from klines.validate import validate_h1


def _parse_args(defaults: dict) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build processed OHLCV datasets from H1 Parquet files")
    parser.add_argument(
        "--symbols",
        type=lambda s: s.split(","),
        default=defaults.get("symbols"),
        metavar="SYMBOL[,SYMBOL...]",
        help="comma-separated symbols to process",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path(defaults.get("raw_dir", "./data/raw")),
        metavar="DIR",
        help="directory containing raw H1 Parquet files (default: ./data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(defaults.get("output_dir", "./data/processed")),
        metavar="DIR",
        help="directory for processed Parquet files (default: ./data/processed)",
    )
    args = parser.parse_args()
    if args.symbols is None:
        parser.error("--symbols is required (e.g. --symbols BTCUSDT,ETHUSDT)")
    return args


def _run(args: argparse.Namespace) -> None:
    for symbol in args.symbols:
        raw_path = args.raw_dir / f"{symbol}_H1.parquet"
        print(f"{symbol}: loading {raw_path}...")
        h1 = load_parquet(raw_path)

        print(f"{symbol}: validating {len(h1)} H1 candles...")
        h1 = validate_h1(h1)

        h4 = aggregate_h4(h1)
        d1 = aggregate_daily(h1)
        w1 = aggregate_weekly(h1)
        m1 = aggregate_monthly(h1)
        q1 = aggregate_quarterly(h1)

        for df, label in [(h4, "H4"), (d1, "D1"), (w1, "W1"), (m1, "M1"), (q1, "Q1")]:
            path = args.output_dir / f"{symbol}_{label}.parquet"
            save_parquet(df, path)
            print(f"{symbol}: {label}={len(df)} candles → {path}")


def main(defaults: dict | None = None) -> None:
    args = _parse_args(defaults or {})
    _run(args)


if __name__ == "__main__":
    main()
