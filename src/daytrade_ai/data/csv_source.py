"""CSV-backed data source. Used by tests + bundled fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from daytrade_ai.data.base import DataSource


class CSVDataSource(DataSource):
    """Loads OHLCV CSV with columns: timestamp,open,high,low,close,volume."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        since: str | None = None,
        until: str | None = None,
    ) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        if "timestamp" not in df.columns:
            raise ValueError(f"CSV {self.path} missing 'timestamp' column")
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")
        df = self.validate(df)
        if since is not None:
            df = df[df.index >= pd.Timestamp(since, tz="UTC")]
        if until is not None:
            df = df[df.index <= pd.Timestamp(until, tz="UTC")]
        return df
