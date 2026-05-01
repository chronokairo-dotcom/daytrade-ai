from __future__ import annotations

import pandas as pd

from daytrade_ai.strategies import get_strategy, list_strategies


def test_registry_lists_built_ins() -> None:
    names = list_strategies()
    for required in ("sma_cross", "rsi_mean_reversion", "momentum"):
        assert required in names


def test_each_strategy_returns_valid_signals(ohlcv_df: pd.DataFrame) -> None:
    for name in list_strategies():
        strat = get_strategy(name)
        sig = strat.generate_signals(ohlcv_df)
        assert isinstance(sig, pd.Series)
        assert sig.index.equals(ohlcv_df.index)
        assert set(sig.unique()).issubset({-1, 0, 1})


def test_sma_cross_invalid_params() -> None:
    import pytest

    with pytest.raises(ValueError):
        get_strategy("sma_cross", fast=30, slow=10)
