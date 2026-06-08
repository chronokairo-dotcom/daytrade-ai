from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
import pandas as pd

from daytrade_ai.backtest.engine import BacktestEngine, BacktestResult
from daytrade_ai.metrics.performance import bootstrap_sharpe_ci
from daytrade_ai.strategies.base import Strategy


class WindowMode(Enum):
    FIXED = auto()
    EXPANDING = auto()
    ROLLING = auto()


@dataclass
class WalkForwardResult:
    fold_results: list[BacktestResult]
    summary: pd.DataFrame
    aggregate: dict[str, float]
    benchmark_fold_results: list[BacktestResult] | None = None
    benchmark_summary: pd.DataFrame | None = None
    bootstrap_ci: tuple[float, float] | None = None


class WalkForward:
    def __init__(
        self,
        engine: BacktestEngine,
        folds: int = 5,
        train_ratio: float = 0.5,
        window_mode: WindowMode = WindowMode.FIXED,
        step_size: int | None = None,
        benchmark_strategy: Strategy | None = None,
    ) -> None:
        if folds < 2:
            raise ValueError("folds must be >= 2")
        if not 0.0 < train_ratio < 1.0:
            raise ValueError("train_ratio must be in (0, 1)")
        self.engine = engine
        self.folds = folds
        self.train_ratio = train_ratio
        self.window_mode = window_mode
        self.step_size = step_size
        self.benchmark_strategy = benchmark_strategy

    def run(self, df: pd.DataFrame, strategy: Strategy) -> WalkForwardResult:
        n = len(df)
        if n < self.folds * 4:
            raise ValueError(f"Not enough rows ({n}) for {self.folds} folds")

        if self.window_mode == WindowMode.FIXED:
            return self._run_fixed(df, strategy)

        return self._run_rolling_anchored(df, strategy)

    def _run_fixed(self, df: pd.DataFrame, strategy: Strategy) -> WalkForwardResult:
        n = len(df)
        fold_size = n // self.folds
        results: list[BacktestResult] = []
        rows: list[dict[str, float]] = []
        bench_results: list[BacktestResult] = []
        bench_rows: list[dict[str, float]] = []

        for k in range(self.folds):
            start = k * fold_size
            end = start + fold_size if k < self.folds - 1 else n
            fold_df = df.iloc[start:end]
            split = max(1, int(len(fold_df) * self.train_ratio))
            train_df = fold_df.iloc[:split]
            test_df = fold_df.iloc[split:]
            if len(test_df) < 5:
                continue

            _ = strategy.generate_signals(train_df)
            res = self.engine.run(test_df, strategy)
            results.append(res)
            rows.append(self._fold_row(k, test_df, res))

            if self.benchmark_strategy is not None:
                bench_res = self.engine.run(test_df, self.benchmark_strategy)
                bench_results.append(bench_res)
                bench_rows.append(self._fold_row(k, test_df, bench_res))

        summary = pd.DataFrame(rows)
        benchmark_summary = pd.DataFrame(bench_rows) if bench_rows else None
        aggregate = self._compute_aggregate(summary)

        return WalkForwardResult(
            fold_results=results,
            summary=summary,
            aggregate=aggregate,
            benchmark_fold_results=bench_results or None,
            benchmark_summary=benchmark_summary,
        )

    def _run_rolling_anchored(self, df: pd.DataFrame, strategy: Strategy) -> WalkForwardResult:
        n = len(df)
        step = self.step_size or (n // self.folds)
        train_len = int(n * self.train_ratio)
        results: list[BacktestResult] = []
        rows: list[dict[str, float]] = []
        bench_results: list[BacktestResult] = []
        bench_rows: list[dict[str, float]] = []

        if self.window_mode == WindowMode.EXPANDING:
            test_start = train_len
            fold_idx = 0
            while test_start < n:
                test_end = min(test_start + step, n)
                if test_end - test_start < 5:
                    break
                train_df = df.iloc[:test_start]
                test_df = df.iloc[test_start:test_end]
                _ = strategy.generate_signals(train_df)
                res = self.engine.run(test_df, strategy)
                results.append(res)
                rows.append(self._fold_row(float(fold_idx), test_df, res))
                if self.benchmark_strategy is not None:
                    bench_res = self.engine.run(test_df, self.benchmark_strategy)
                    bench_results.append(bench_res)
                    bench_rows.append(self._fold_row(float(fold_idx), test_df, bench_res))
                test_start += step
                fold_idx += 1

        elif self.window_mode == WindowMode.ROLLING:
            train_window = train_len
            test_start = train_len
            fold_idx = 0
            while test_start < n:
                test_end = min(test_start + step, n)
                if test_end - test_start < 5:
                    break
                train_start = max(0, test_start - train_window)
                train_df = df.iloc[train_start:test_start]
                test_df = df.iloc[test_start:test_end]
                _ = strategy.generate_signals(train_df)
                res = self.engine.run(test_df, strategy)
                results.append(res)
                rows.append(self._fold_row(float(fold_idx), test_df, res))
                if self.benchmark_strategy is not None:
                    bench_res = self.engine.run(test_df, self.benchmark_strategy)
                    bench_results.append(bench_res)
                    bench_rows.append(self._fold_row(float(fold_idx), test_df, bench_res))
                test_start += step
                fold_idx += 1

        summary = pd.DataFrame(rows)
        benchmark_summary = pd.DataFrame(bench_rows) if bench_rows else None
        aggregate = self._compute_aggregate(summary)

        sharpes = summary["sharpe"].dropna().to_numpy(dtype=float)
        if len(sharpes) >= 4:
            ci = bootstrap_sharpe_ci(sharpes, n_resamples=2000, seed=42)
        else:
            ci = (float(sharpes.mean()), float(sharpes.mean())) if len(sharpes) else (0.0, 0.0)

        return WalkForwardResult(
            fold_results=results,
            summary=summary,
            aggregate=aggregate,
            benchmark_fold_results=bench_results or None,
            benchmark_summary=benchmark_summary,
            bootstrap_ci=ci,
        )

    def _fold_row(self, k: float, test_df: pd.DataFrame, res: BacktestResult) -> dict[str, float]:
        return {
            "fold": k,
            "n_bars": float(len(test_df)),
            "total_return": float(res.metrics.get("total_return", 0.0)),
            "sharpe": float(res.metrics.get("sharpe", 0.0)),
            "max_drawdown": float(res.metrics.get("max_drawdown", 0.0)),
            "n_trades": float(res.metrics.get("n_trades", 0.0)),
        }

    def _compute_aggregate(self, summary: pd.DataFrame) -> dict[str, float]:
        if summary.empty:
            return {
                "mean_sharpe": 0.0,
                "median_sharpe": 0.0,
                "mean_total_return": 0.0,
                "mean_max_drawdown": 0.0,
                "win_folds": 0.0,
                "total_folds": 0.0,
            }
        return {
            "mean_sharpe": float(summary["sharpe"].mean()),
            "median_sharpe": float(summary["sharpe"].median()),
            "mean_total_return": float(summary["total_return"].mean()),
            "mean_max_drawdown": float(summary["max_drawdown"].mean()),
            "win_folds": float((summary["total_return"] > 0).sum()),
            "total_folds": float(len(summary)),
        }


__all__ = ["WalkForward", "WalkForwardResult", "WindowMode"]

_ = np
