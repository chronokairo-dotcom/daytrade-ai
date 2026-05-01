"""Walk-forward analysis: split data into N folds, run backtest on each test fold."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from daytrade_ai.backtest.engine import BacktestEngine, BacktestResult
from daytrade_ai.strategies.base import Strategy


@dataclass
class WalkForwardResult:
    fold_results: list[BacktestResult]
    summary: pd.DataFrame  # one row per fold with key metrics
    aggregate: dict[str, float]


class WalkForward:
    """Rolling walk-forward backtest.

    For non-parametric strategies (the ones bundled), the "fit" stage is a
    no-op sanity check: we make sure the train window has > 0 rows and that
    the strategy can produce signals on it. The reported metrics come from
    the test window only.
    """

    def __init__(
        self,
        engine: BacktestEngine,
        folds: int = 5,
        train_ratio: float = 0.5,
    ) -> None:
        if folds < 2:
            raise ValueError("folds must be >= 2")
        if not 0.0 < train_ratio < 1.0:
            raise ValueError("train_ratio must be in (0, 1)")
        self.engine = engine
        self.folds = folds
        self.train_ratio = train_ratio

    def run(self, df: pd.DataFrame, strategy: Strategy) -> WalkForwardResult:
        n = len(df)
        if n < self.folds * 4:
            raise ValueError(f"Not enough rows ({n}) for {self.folds} folds")

        fold_size = n // self.folds
        results: list[BacktestResult] = []
        rows: list[dict[str, float]] = []

        for k in range(self.folds):
            start = k * fold_size
            end = start + fold_size if k < self.folds - 1 else n
            fold_df = df.iloc[start:end]
            split = max(1, int(len(fold_df) * self.train_ratio))
            train_df = fold_df.iloc[:split]
            test_df = fold_df.iloc[split:]
            if len(test_df) < 5:
                continue

            # Sanity-check fit: ensure strategy can produce signals on train.
            _ = strategy.generate_signals(train_df)

            res = self.engine.run(test_df, strategy)
            results.append(res)
            rows.append(
                {
                    "fold": float(k),
                    "n_bars": float(len(test_df)),
                    "total_return": float(res.metrics.get("total_return", 0.0)),
                    "sharpe": float(res.metrics.get("sharpe", 0.0)),
                    "max_drawdown": float(res.metrics.get("max_drawdown", 0.0)),
                    "n_trades": float(res.metrics.get("n_trades", 0.0)),
                }
            )

        summary = pd.DataFrame(rows)
        if summary.empty:
            aggregate = {"mean_sharpe": 0.0, "mean_total_return": 0.0, "mean_max_drawdown": 0.0}
        else:
            aggregate = {
                "mean_sharpe": float(summary["sharpe"].mean()),
                "median_sharpe": float(summary["sharpe"].median()),
                "mean_total_return": float(summary["total_return"].mean()),
                "mean_max_drawdown": float(summary["max_drawdown"].mean()),
                "win_folds": float((summary["total_return"] > 0).sum()),
                "total_folds": float(len(summary)),
            }
        _ = np
        return WalkForwardResult(fold_results=results, summary=summary, aggregate=aggregate)
