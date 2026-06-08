from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from daytrade_ai.backtest.engine import BacktestEngine
from daytrade_ai.strategies.base import Strategy, register


@register("oracle")
class OracleStrategy(Strategy):
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"].to_numpy(dtype=float)
        out = np.ones(len(df), dtype=int)
        for i in range(1, len(df)):
            out[i] = 1 if close[i] > close[i - 1] else 0
        return pd.Series(out, index=df.index, dtype="int64", name="signal")


def test_engine_recovers_known_edge() -> None:
    rng = np.random.default_rng(42)
    n = 2000
    drift = 0.0003
    noise_scale = 0.002
    price = 100.0
    prices: list[float] = [price]
    for _ in range(n - 1):
        price *= 1.0 + drift + rng.normal(0, noise_scale)
        prices.append(price)
    dates = pd.date_range("2020-01-01", periods=n, freq="h")
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.001 for p in prices],
            "low": [p * 0.999 for p in prices],
            "close": prices,
            "volume": [100.0] * n,
        },
        index=dates,
    )

    engine = BacktestEngine(
        initial_cash=10_000.0,
        fee_bps=1.0,
        slippage_bps=0.0,
        zero_cost_mode=False,
    )
    oracle = OracleStrategy()
    result = engine.run(df, oracle)

    assert result.metrics["sharpe"] > 0.0, (
        f"Oracle strategy should produce non-negative Sharpe, got {result.metrics['sharpe']:.3f}"
    )
    assert result.metrics["n_trades"] > 10


def test_engine_zero_cost_matches_oracle() -> None:
    rng = np.random.default_rng(7)
    n = 500
    price = 100.0
    prices: list[float] = [price]
    for _ in range(n - 1):
        price *= 1.0 + rng.normal(0.0005, 0.01)
        prices.append(price)
    dates = pd.date_range("2020-06-01", periods=n, freq="h")
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.002 for p in prices],
            "low": [p * 0.998 for p in prices],
            "close": prices,
            "volume": [100.0] * n,
        },
        index=dates,
    )

    cost_engine = BacktestEngine(
        initial_cash=10_000.0,
        fee_bps=10.0,
        slippage_bps=5.0,
        zero_cost_mode=False,
    )
    zero_engine = BacktestEngine(
        initial_cash=10_000.0,
        fee_bps=10.0,
        slippage_bps=5.0,
        zero_cost_mode=True,
    )
    oracle = OracleStrategy()
    cost_result = cost_engine.run(df, oracle)
    zero_result = zero_engine.run(df, oracle)

    assert zero_result.metrics["total_return"] >= cost_result.metrics["total_return"], (
        "Zero-cost run should have >= return vs costly run"
    )
    assert zero_result.metrics["n_trades"] == cost_result.metrics["n_trades"], (
        "Trade count should be identical regardless of cost mode"
    )


if __name__ == "__main__":
    pytest.main([__file__])
