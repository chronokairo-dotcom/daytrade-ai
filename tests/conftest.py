"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "btc_sample.csv"


@pytest.fixture(scope="session")
def fixture_path() -> Path:
    return FIXTURE_PATH


@pytest.fixture(scope="session")
def ohlcv_df(fixture_path: Path) -> pd.DataFrame:
    from daytrade_ai.data.csv_source import CSVDataSource

    return CSVDataSource(fixture_path).fetch("BTC/USDT", "1h")
