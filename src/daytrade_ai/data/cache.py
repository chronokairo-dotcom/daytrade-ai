"""Parquet cache helpers for OHLCV frames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def cache_path(cache_dir: Path, exchange: str, symbol: str, timeframe: str) -> Path:
    safe_symbol = symbol.replace("/", "-").replace(":", "_")
    return cache_dir / exchange / f"{safe_symbol}__{timeframe}.parquet"


def write_cache(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def read_cache(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_parquet(path)
