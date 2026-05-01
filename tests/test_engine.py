from __future__ import annotations

import pandas as pd

from daytrade_ai.backtest.engine import BacktestEngine
from daytrade_ai.strategies import get_strategy


def test_backtest_runs_and_is_reproducible(ohlcv_df: pd.DataFrame) -> None:
    strat = get_strategy("sma_cross", fast=5, slow=20)
    eng = BacktestEngine(initial_cash=10_000, fee_bps=10, slippage_bps=5)
    r1 = eng.run(ohlcv_df, strat)
    r2 = eng.run(ohlcv_df, strat)
    assert r1.metrics == r2.metrics
    assert r1.equity_curve.equals(r2.equity_curve)
    assert len(r1.equity_curve) == len(ohlcv_df)


def test_zero_fee_zero_slippage_fewer_costs(ohlcv_df: pd.DataFrame) -> None:
    strat = get_strategy("sma_cross", fast=5, slow=20)
    eng_costly = BacktestEngine(initial_cash=10_000, fee_bps=50, slippage_bps=20)
    eng_free = BacktestEngine(initial_cash=10_000, fee_bps=0, slippage_bps=0)
    r_costly = eng_costly.run(ohlcv_df, strat)
    r_free = eng_free.run(ohlcv_df, strat)
    if r_costly.trades:
        # Free version should not be worse than costly version on same trades.
        assert r_free.metrics["total_return"] >= r_costly.metrics["total_return"] - 1e-9


def test_no_trades_means_flat_equity(ohlcv_df: pd.DataFrame) -> None:
    # momentum with absurd threshold => no signals
    strat = get_strategy("momentum", lookback=20, threshold=10.0)
    eng = BacktestEngine(initial_cash=10_000, fee_bps=10, slippage_bps=5)
    r = eng.run(ohlcv_df, strat)
    assert r.metrics["n_trades"] == 0
    assert abs(r.metrics["total_return"]) < 1e-9
    assert abs(r.equity_curve.iloc[-1] - 10_000.0) < 1e-6


def test_signals_have_no_lookahead(ohlcv_df: pd.DataFrame) -> None:
    """If we truncate the data and run, the early portion of equity must match."""
    strat = get_strategy("sma_cross", fast=5, slow=20)
    eng = BacktestEngine(initial_cash=10_000, fee_bps=10, slippage_bps=5)
    full = eng.run(ohlcv_df, strat)
    half = eng.run(ohlcv_df.iloc[:120], strat)
    # The first 100 bars of equity should match between the two runs (no lookahead).
    common = min(len(full.equity_curve), len(half.equity_curve), 100)
    pd.testing.assert_series_equal(
        full.equity_curve.iloc[:common],
        half.equity_curve.iloc[:common],
        check_names=False,
    )
