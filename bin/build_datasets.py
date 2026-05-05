#!/usr/bin/env python3
"""Validate raw H1 data and build H4/D1/W1/M1/Q1 processed datasets."""

import argparse
import logging
from pathlib import Path

from klines.pipeline import build


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


def main(defaults: dict | None = None) -> None:
    args = _parse_args(defaults or {})
    build(args.symbols, args.raw_dir, args.output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
