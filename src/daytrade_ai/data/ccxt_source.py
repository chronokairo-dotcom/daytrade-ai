"""ccxt-backed OHLCV data source with parquet cache."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd

from daytrade_ai.data.base import DataSource
from daytrade_ai.data.cache import cache_path, read_cache, write_cache


class CCXTDataSource(DataSource):
    """Fetch OHLCV from any ccxt exchange. Read-only by design."""

    def __init__(
        self,
        exchange: str = "binance",
        cache_dir: Path | str = "data/cache",
        rate_limit_ms: int = 250,
    ) -> None:
        self.exchange_name = exchange
        self.cache_dir = Path(cache_dir)
        self.rate_limit_ms = rate_limit_ms
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            import ccxt  # imported lazily to keep tests offline

            cls = getattr(ccxt, self.exchange_name)
            self._client = cls({"enableRateLimit": True})
        return self._client

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        since: str | None = None,
        until: str | None = None,
    ) -> pd.DataFrame:
        # Try cache first.
        path = cache_path(self.cache_dir, self.exchange_name, symbol, timeframe)
        cached = read_cache(path)
        if cached is not None:
            df = self.validate(cached)
            if since is not None:
                df = df[df.index >= pd.Timestamp(since, tz="UTC")]
            if until is not None:
                df = df[df.index <= pd.Timestamp(until, tz="UTC")]
            if not df.empty:
                return df

        df = self._fetch_remote(symbol, timeframe, since, until)
        write_cache(df, path)
        return df

    def _fetch_remote(
        self,
        symbol: str,
        timeframe: str,
        since: str | None,
        until: str | None,
    ) -> pd.DataFrame:
        client = self._get_client()
        since_ms: int | None = None
        if since is not None:
            since_ms = int(pd.Timestamp(since, tz="UTC").timestamp() * 1000)
        until_ms: int | None = None
        if until is not None:
            until_ms = int(pd.Timestamp(until, tz="UTC").timestamp() * 1000)

        all_rows: list[list[float]] = []
        cursor = since_ms
        limit = 1000
        while True:
            batch = client.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=limit)
            if not batch:
                break
            all_rows.extend(batch)
            last_ts = batch[-1][0]
            if cursor is not None and last_ts <= cursor:
                break
            cursor = last_ts + 1
            if until_ms is not None and last_ts >= until_ms:
                break
            if len(batch) < limit:
                break
            time.sleep(self.rate_limit_ms / 1000.0)

        if not all_rows:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume"],
                index=pd.DatetimeIndex([], tz="UTC", name="timestamp"),
            )

        df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp")
        return self.validate(df)
