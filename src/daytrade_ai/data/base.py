"""Abstract data source."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataSource(ABC):
    """OHLCV data source. Returns a DataFrame indexed by UTC timestamp."""

    @abstractmethod
    def fetch(
        self,
        symbol: str,
        timeframe: str,
        since: str | None = None,
        until: str | None = None,
    ) -> pd.DataFrame:
        """Return OHLCV DataFrame indexed by UTC datetime with columns
        open, high, low, close, volume."""

    @staticmethod
    def validate(df: pd.DataFrame) -> pd.DataFrame:
        """Validate + normalize an OHLCV frame."""
        missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"OHLCV frame missing columns: {missing}")
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("OHLCV frame must be indexed by DatetimeIndex")
        df = df.tz_localize("UTC") if df.index.tz is None else df.tz_convert("UTC")
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]
        return df[OHLCV_COLUMNS].astype(float)
