"""Performance metrics: sharpe, sortino, calmar, max drawdown, win rate, etc."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from daytrade_ai.backtest.portfolio import Trade


class PerformanceMetrics:
    """Compute performance metrics from an equity curve + trades list."""

    def __init__(self, bars_per_year: float = 365.0 * 24.0) -> None:
        self.bars_per_year = bars_per_year

    # ------------------------------------------------------------------
    def compute(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        trades: list[Trade],
    ) -> dict[str, float]:
        if equity_curve.empty:
            return self._empty()

        first = float(equity_curve.iloc[0])
        last = float(equity_curve.iloc[-1])
        total_return = last / first - 1.0 if first else 0.0

        n_bars = max(len(equity_curve), 1)
        years = n_bars / self.bars_per_year if self.bars_per_year > 0 else 0.0
        if years > 0 and first > 0 and last > 0:
            cagr = (last / first) ** (1.0 / years) - 1.0
        else:
            cagr = 0.0

        sharpe = self._sharpe(returns)
        sortino = self._sortino(returns)
        max_dd = self._max_drawdown(equity_curve)
        calmar = (cagr / abs(max_dd)) if max_dd < 0 else 0.0

        if trades:
            wins = [t for t in trades if t.pnl > 0]
            losses = [t for t in trades if t.pnl <= 0]
            win_rate = len(wins) / len(trades)
            gross_win = float(sum(t.pnl for t in wins))
            gross_loss = float(sum(-t.pnl for t in losses))
            profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
            avg_win = float(np.mean([t.pnl for t in wins])) if wins else 0.0
            avg_loss = float(np.mean([t.pnl for t in losses])) if losses else 0.0
            expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss
        else:
            win_rate = 0.0
            profit_factor = 0.0
            expectancy = 0.0

        return {
            "total_return": float(total_return),
            "cagr": float(cagr),
            "sharpe": float(sharpe),
            "sortino": float(sortino),
            "calmar": float(calmar),
            "max_drawdown": float(max_dd),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "expectancy": float(expectancy),
            "n_trades": float(len(trades)),
            "n_bars": float(n_bars),
        }

    # ------------------------------------------------------------------
    def _sharpe(self, returns: pd.Series) -> float:
        if returns.empty:
            return 0.0
        std = float(returns.std(ddof=0))
        if std == 0.0:
            return 0.0
        mean = float(returns.mean())
        return float(mean / std * np.sqrt(self.bars_per_year))

    def _sortino(self, returns: pd.Series) -> float:
        if returns.empty:
            return 0.0
        downside = returns.clip(upper=0.0)
        dd_std = float(np.sqrt((downside**2).mean()))
        if dd_std == 0.0:
            return 0.0
        mean = float(returns.mean())
        return float(mean / dd_std * np.sqrt(self.bars_per_year))

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        running_max = equity.cummax()
        drawdown = equity / running_max - 1.0
        return float(drawdown.min()) if len(drawdown) else 0.0

    @staticmethod
    def _empty() -> dict[str, float]:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "calmar": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "n_trades": 0.0,
            "n_bars": 0.0,
        }
