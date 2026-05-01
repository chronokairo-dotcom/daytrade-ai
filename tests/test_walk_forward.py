from __future__ import annotations

import pandas as pd

from daytrade_ai.backtest.engine import BacktestEngine
from daytrade_ai.backtest.walk_forward import WalkForward
from daytrade_ai.strategies import get_strategy


def test_walk_forward_runs(ohlcv_df: pd.DataFrame) -> None:
    eng = BacktestEngine(initial_cash=10_000, fee_bps=10, slippage_bps=5)
    wf = WalkForward(engine=eng, folds=4, train_ratio=0.5)
    res = wf.run(ohlcv_df, get_strategy("sma_cross", fast=5, slow=20))
    assert len(res.fold_results) >= 1
    assert "mean_sharpe" in res.aggregate
    assert {"fold", "n_bars", "total_return", "sharpe", "max_drawdown"}.issubset(
        set(res.summary.columns)
    )


def test_walk_forward_too_few_bars() -> None:
    import pytest

    df = pd.DataFrame(
        {
            "open": [1, 2, 3],
            "high": [1, 2, 3],
            "low": [1, 2, 3],
            "close": [1, 2, 3],
            "volume": [1, 1, 1],
        },
        index=pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC"),
    )
    eng = BacktestEngine()
    wf = WalkForward(engine=eng, folds=5)
    with pytest.raises(ValueError):
        wf.run(df, get_strategy("sma_cross"))
