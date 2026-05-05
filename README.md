# klines

Fetch, normalise, validate, and aggregate Binance OHLCV klines into clean Parquet datasets.

## What it does

Two ready-to-run scripts and five library modules, no trading logic, no config globals:

| | Name | What it provides |
|---|---|---|
| script | `bin/fetch_data.py` | Download klines from Binance and save as Parquet |
| script | `bin/build_datasets.py` | Validate and aggregate H1 or M15 data into H1/H4/D1/W1/M1/Q1 |
| lib | `download` | Async batch HTTP fetch from Binance REST API |
| lib | `normalise` | Convert raw Binance JSON rows to typed OHLCV DataFrame |
| lib | `store` | Save and load DataFrames as Parquet files |
| lib | `validate` | Deduplicate, gap-fill, and sanity-check H1 or M15 data |
| lib | `aggregate` | Resample M15→H1 and H1→H4/D1/W1/M1/Q1 |

## Install

```bash
pip install "klines @ git+https://github.com/jeromer/klines.git"
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add "klines @ git+https://github.com/jeromer/klines.git"
```

## Scripts

The scripts in `bin/` are executable and self-contained. Two ways to run them:

**From a clone** (no install required, needs deps on `$PYTHONPATH`):
```bash
git clone https://github.com/jeromer/klines
cd klines
uv sync
./bin/fetch_data.py --symbols BTCUSDT,ETHUSDT
./bin/build_datasets.py --symbols BTCUSDT,ETHUSDT
```

**As installed CLI commands** (after `pip install` / `uv add`):
```bash
binance-fetch --symbols BTCUSDT,ETHUSDT
binance-build --symbols BTCUSDT,ETHUSDT
```

Both forms accept identical flags.

### `bin/fetch_data.py` — download klines

```
./bin/fetch_data.py [--symbols SYMBOL[,SYMBOL...]]
                    [--market spot|futures]
                    [--interval m15|h1|h4|d]
                    [--start YYYY-MM-DD]
                    [--end YYYY-MM-DD]
                    [--output-dir DIR]
                    [--workers N]
                    [--progress|--no-progress]
```

Downloads H1 klines (default) for one or more symbols. Resumes from the last stored timestamp if a Parquet file already exists.

```bash
# fetch BTC + ETH hourly from 2020 to today → data/raw/
./bin/fetch_data.py --symbols BTCUSDT,ETHUSDT --start 2020-01-01

# fetch 15m futures data into a custom dir
./bin/fetch_data.py --symbols BTCUSDT --market futures --interval m15 --output-dir /tmp/raw
```

Defaults: `--market spot`, `--interval h1`, `--start 2017-01-01`, `--output-dir ./data/raw`, `--workers <CPU count>`.

### `bin/build_datasets.py` — validate and aggregate

```
./bin/build_datasets.py [--symbols SYMBOL[,SYMBOL...]]
                        [--source-interval h1|m15]
                        [--raw-dir DIR]
                        [--output-dir DIR]
```

Reads `{symbol}_{SOURCE}.parquet` from `--raw-dir`, validates, and writes H1/H4/D1/W1/M1/Q1 Parquet files to `--output-dir`. When `--source-interval m15`, H1 is derived from M15 before aggregating higher timeframes.

```bash
# build from H1 source (default)
./bin/build_datasets.py --symbols BTCUSDT,ETHUSDT

# build from M15 source — derives H1, H4, D1, W1, M1, Q1
./bin/build_datasets.py --symbols BTCUSDT,ETHUSDT --source-interval m15

./bin/build_datasets.py --symbols BTCUSDT --raw-dir /tmp/raw --output-dir /tmp/processed
```

Defaults: `--source-interval h1`, `--raw-dir ./data/raw`, `--output-dir ./data/processed`.

### Full pipeline

```bash
# H1 source
./bin/fetch_data.py --symbols BTCUSDT,ETHUSDT && ./bin/build_datasets.py --symbols BTCUSDT,ETHUSDT

# M15 source — higher resolution, derives H1 and all higher timeframes
./bin/fetch_data.py --symbols BTCUSDT,ETHUSDT --interval m15 && \
./bin/build_datasets.py --symbols BTCUSDT,ETHUSDT --source-interval m15
```

## Embedding

Use this when your project has its own config and wants to call the pipeline programmatically rather than shelling out to the scripts.

### Option A — call `main()` with your defaults

Both scripts expose `main(defaults={...})`. Keys in `defaults` set argument defaults; any CLI flag passed at runtime still overrides them. Your project never needs to touch `sys.argv`.

```python
from bin.fetch_data import main as fetch_main
from bin.build_datasets import main as build_main

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
RAW_DIR = "/data/raw"
PROCESSED_DIR = "/data/processed"

# equivalent to: ./bin/fetch_data.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --output-dir /data/raw
fetch_main(defaults={
    "symbols": SYMBOLS,
    "start": "2017-01-01",
    "output_dir": RAW_DIR,
})

# equivalent to: ./bin/build_datasets.py --symbols ... --raw-dir /data/raw --output-dir /data/processed
build_main(defaults={
    "symbols": SYMBOLS,
    "raw_dir": RAW_DIR,
    "output_dir": PROCESSED_DIR,
})
```

### Option B — call library functions directly

Use this when you need finer control: custom progress reporting, in-memory pipelines, partial steps, or integration with an async event loop.

```python
import asyncio
from pathlib import Path

import pandas as pd

from klines.download import KlineRequest, fetch_all
from klines.normalise import normalise_klines
from klines.store import load_parquet, save_parquet
from klines.validate import validate_h1
from klines.aggregate import aggregate_h4, aggregate_daily

RAW_DIR = Path("/data/raw")
PROCESSED_DIR = Path("/data/processed")
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
START = "2017-01-01"


async def fetch(symbols: list[str]) -> None:
    end_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    requests = []
    for symbol in symbols:
        path = RAW_DIR / f"{symbol}_H1.parquet"
        if path.exists():
            start_ms = int(load_parquet(path).index[-1].timestamp() * 1000) + 1
        else:
            start_ms = int(pd.Timestamp(START, tz="UTC").timestamp() * 1000)
        requests.append(KlineRequest(symbol, "1h", start_ms, end_ms))

    raw = await fetch_all(requests, max_workers=4)

    for symbol, raw_df in raw.items():
        new_df = normalise_klines(raw_df)
        path = RAW_DIR / f"{symbol}_H1.parquet"
        if path.exists():
            old = load_parquet(path)
            new_df = pd.concat([old, new_df]).sort_index()
            new_df = new_df[~new_df.index.duplicated(keep="last")]
        save_parquet(new_df, path)


def build(symbols: list[str]) -> None:
    for symbol in symbols:
        h1 = validate_h1(load_parquet(RAW_DIR / f"{symbol}_H1.parquet"))
        save_parquet(aggregate_h4(h1),    PROCESSED_DIR / f"{symbol}_H4.parquet")
        save_parquet(aggregate_daily(h1), PROCESSED_DIR / f"{symbol}_D1.parquet")


asyncio.run(fetch(SYMBOLS))
build(SYMBOLS)
```

## API reference

### `download`

```python
from klines.download import KlineRequest, fetch_all, SPOT_URL, FUTURES_URL, MAX_BARS_PER_REQUEST

# SPOT_URL    = "https://api.binance.com/api/v3/klines"
# FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"
# MAX_BARS_PER_REQUEST = 1000  (Binance hard limit; fetch_all batches automatically)

req = KlineRequest(
    symbol="BTCUSDT",
    interval="1h",       # 15m | 1h | 4h | 1d
    start_ms=...,        # Unix ms
    end_ms=...,          # Unix ms
    url=SPOT_URL,        # default
)

result: dict[str, pd.DataFrame] = asyncio.run(
    fetch_all(requests, max_workers=4, on_progress=None)
)
# on_progress: Callable[[symbol: str, done: int, total: int], None]
```

### `normalise`

```python
from klines.normalise import normalise_klines

df = normalise_klines(raw_df)
# Input:  raw DataFrame from fetch_all (12 Binance columns)
# Output: UTC DatetimeIndex, columns [open, high, low, close, volume] float64
#         Handles Binance's ms→μs timestamp switch at 2025-01-01
#         Deduplicates automatically
```

### `store`

```python
from klines.store import save_parquet, load_parquet

save_parquet(df, Path("data/BTCUSDT_H1.parquet"))   # creates parent dirs
df = load_parquet(Path("data/BTCUSDT_H1.parquet"))  # UTC index preserved
```

### `validate`

```python
from klines.validate import validate_h1, validate_m15

df = validate_h1(df)   # for H1 source data
df = validate_m15(df)  # for M15 source data
# Both:
# - Drop duplicate timestamps (keeps last)
# - Forward-fill gaps with zero-volume candles (O=H=L=C=prev close)
# - Raise ValueError on OHLC sanity violations
# - Drop the last candle if its period hasn't closed
```

Individual functions:

```python
from klines.validate import (
    check_no_gaps,       # raises ValueError if any gap found
    check_no_duplicates, # raises ValueError if duplicate timestamps found
    check_ohlc_sanity,   # raises ValueError on high<low, negative volume, etc.
    fill_gaps,           # forward-fill missing bars (freq param: "1h" or "15min")
    drop_partial_candle, # remove last bar if its period hasn't closed
)
```

### `aggregate`

```python
from klines.aggregate import (
    aggregate_h1,         # M15 → H1 (requires all 4 bars per hour)
    aggregate_h4,         # H1 → 4h bars, UTC-anchored to 2020-01-01
    aggregate_daily,      # H1 → daily bars, midnight UTC
    aggregate_weekly,     # H1 → weekly bars, Monday 00:00 UTC
    aggregate_monthly,    # H1 → monthly bars, 1st of month UTC
    aggregate_quarterly,  # H1 → quarterly bars, Jan/Apr/Jul/Oct 1st UTC
)
```

Incomplete periods at the tail are dropped (e.g. a partial week with fewer than 144 H1 bars).

## Development

```bash
git clone https://github.com/jeromer/klines
cd klines
uv sync --extra dev
uv run pytest tests/
uv run ruff check .
```

## Requirements

- Python ≥ 3.12
- pandas ≥ 2.2
- aiohttp ≥ 3.9
- pyarrow ≥ 15
