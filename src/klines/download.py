import asyncio
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

import aiohttp
import pandas as pd

SPOT_URL: str = "https://api.binance.com/api/v3/klines"
FUTURES_URL: str = "https://fapi.binance.com/fapi/v1/klines"
MAX_BARS_PER_REQUEST: int = 1000

_INTERVAL_MS: dict[str, int] = {
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

_RAW_COLUMN_COUNT = 12

ProgressCallback = Callable[[str, int, int], None]


@dataclass(frozen=True)
class KlineRequest:
    symbol: str
    interval: str
    start_ms: int
    end_ms: int
    url: str = field(default=SPOT_URL)


async def fetch_all(
    requests: list[KlineRequest],
    max_workers: int,
    on_progress: ProgressCallback | None = None,
) -> dict[str, pd.DataFrame]:
    semaphore = asyncio.Semaphore(max_workers)
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_symbol(session, semaphore, req, on_progress) for req in requests]
        results = await asyncio.gather(*tasks)
    return {req.symbol: df for req, df in zip(requests, results)}


async def _fetch_symbol(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    req: KlineRequest,
    on_progress: ProgressCallback | None,
) -> pd.DataFrame:
    interval_ms = _INTERVAL_MS[req.interval]
    batch_starts = list(range(req.start_ms, req.end_ms, MAX_BARS_PER_REQUEST * interval_ms))
    total = len(batch_starts)
    counter: dict[str, int] = defaultdict(int)

    tasks = [
        _fetch_batch(
            session,
            semaphore,
            req.symbol,
            req.interval,
            req.url,
            start,
            req.end_ms,
            counter,
            total,
            on_progress,
        )
        for start in batch_starts
    ]
    batches = await asyncio.gather(*tasks)
    rows = [row for batch in batches for row in batch]
    return pd.DataFrame(rows, columns=range(_RAW_COLUMN_COUNT))


async def _fetch_batch(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    symbol: str,
    interval: str,
    url: str,
    start_ms: int,
    end_ms: int,
    counter: dict[str, int],
    total: int,
    on_progress: ProgressCallback | None,
) -> list[list]:
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms - 1,
        "limit": MAX_BARS_PER_REQUEST,
    }
    async with semaphore:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

    counter["done"] += 1
    if on_progress is not None:
        on_progress(symbol, counter["done"], total)

    return data
