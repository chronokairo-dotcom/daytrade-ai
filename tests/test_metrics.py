from __future__ import annotations

import numpy as np
import pandas as pd

from daytrade_ai.metrics.performance import PerformanceMetrics


def test_metrics_empty() -> None:
    pm = PerformanceMetrics(bars_per_year=365 * 24)
    out = pm.compute(pd.Series(dtype=float), pd.Series(dtype=float), [])
    assert out["sharpe"] == 0.0
    assert out["max_drawdown"] == 0.0


def test_metrics_basic_positive_drift() -> None:
    pm = PerformanceMetrics(bars_per_year=252)
    rng = np.random.default_rng(0)
    rets = pd.Series(rng.normal(0.001, 0.01, 1000))
    equity = (1.0 + rets).cumprod() * 1000.0
    out = pm.compute(equity, rets, [])
    assert out["total_return"] > 0
    assert out["sharpe"] > 0
    assert out["max_drawdown"] <= 0.0
    assert out["sortino"] >= out["sharpe"] * 0.5  # sortino tends to >= sharpe-ish


def test_max_drawdown_known() -> None:
    eq = pd.Series([100, 120, 90, 110])
    pm = PerformanceMetrics()
    rets = eq.pct_change().fillna(0)
    out = pm.compute(eq, rets, [])
    # peak 120, trough 90 => -25%
    assert abs(out["max_drawdown"] - (-0.25)) < 1e-9
