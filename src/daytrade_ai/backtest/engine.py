from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from daytrade_ai.backtest.portfolio import Portfolio, Trade
from daytrade_ai.metrics.performance import PerformanceMetrics
from daytrade_ai.strategies.base import Strategy


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[Trade]
    metrics: dict[str, float]
    signals: pd.Series
    df: pd.DataFrame = field(repr=False)
    initial_cash: float = 0.0
    fee_bps: float = 0.0
    slippage_bps: float = 0.0

    @property
    def total_return(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        first = float(self.equity_curve.iloc[0])
        last = float(self.equity_curve.iloc[-1])
        return last / first - 1.0 if first else 0.0


class BacktestEngine:
    def __init__(
        self,
        initial_cash: float = 10_000.0,
        fee_bps: float = 10.0,
        slippage_bps: float = 5.0,
        bars_per_year: float = 365.0 * 24.0,
        maker_fee_bps: float = 1.0,
        use_taker_fee: bool = True,
        zero_cost_mode: bool = False,
        min_bars_between_trades: int = 0,
    ) -> None:
        self.initial_cash = initial_cash
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.bars_per_year = bars_per_year
        self.maker_fee_bps = maker_fee_bps
        self.use_taker_fee = use_taker_fee
        self.zero_cost_mode = zero_cost_mode
        self.min_bars_between_trades = min_bars_between_trades

    def _effective_fee_bps(self) -> float:
        if self.zero_cost_mode:
            return 0.0
        return self.fee_bps if self.use_taker_fee else self.maker_fee_bps

    def _effective_slippage_bps(self) -> float:
        if self.zero_cost_mode:
            return 0.0
        return self.slippage_bps

    def _exec_price(self, base: float, side: int) -> float:
        slip = self._effective_slippage_bps() / 10_000.0
        return base * (1.0 + slip) if side > 0 else base * (1.0 - slip)

    def _fee(self, notional: float) -> float:
        bps = self._effective_fee_bps()
        return abs(notional) * (bps / 10_000.0)

    def run(self, df: pd.DataFrame, strategy: Strategy) -> BacktestResult:
        df = df.copy()
        signals = strategy.generate_signals(df).astype(int)
        target_pos = signals.shift(1).fillna(0).astype(int)

        portfolio = Portfolio(initial_cash=self.initial_cash)
        equity_index: list[Any] = []
        equity_values: list[float] = []

        opens = df["open"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)
        targets = target_pos.to_numpy(dtype=int)
        ts_index = df.index

        current_side = 0
        bars_since_last_trade = self.min_bars_between_trades + 1

        for i in range(len(df)):
            target = int(targets[i])
            o = float(opens[i])
            c = float(closes[i])
            ts = ts_index[i]
            bars_since_last_trade += 1

            if target != current_side and bars_since_last_trade >= self.min_bars_between_trades:
                if current_side != 0 and portfolio.position != 0.0:
                    exit_side = -current_side
                    exit_price = self._exec_price(o, exit_side)
                    notional = exit_price * abs(portfolio.position)
                    fee = self._fee(notional)
                    portfolio.cash += portfolio.position * exit_price - fee
                    portfolio.fees_total += fee
                    assert portfolio.last_entry_time is not None
                    pnl_per_unit = (exit_price - portfolio.avg_entry) * current_side
                    pnl = pnl_per_unit * abs(portfolio.position) - fee
                    portfolio.trades.append(
                        Trade(
                            entry_time=portfolio.last_entry_time,
                            exit_time=ts,
                            side=current_side,
                            entry_price=portfolio.avg_entry,
                            exit_price=exit_price,
                            size=abs(portfolio.position),
                            fees_paid=fee,
                            pnl=pnl,
                        )
                    )
                    portfolio.position = 0.0
                    portfolio.avg_entry = 0.0
                    portfolio.last_entry_time = None
                    current_side = 0

                if target != 0:
                    entry_price = self._exec_price(o, target)
                    alloc = portfolio.cash * 0.99
                    if alloc <= 0:
                        target = 0
                    else:
                        size_units = alloc / entry_price
                        notional = entry_price * size_units
                        fee = self._fee(notional)
                        portfolio.cash -= target * notional + fee
                        portfolio.position = target * size_units
                        portfolio.avg_entry = entry_price
                        portfolio.last_entry_time = ts
                        portfolio.fees_total += fee
                        current_side = target
                        bars_since_last_trade = 0

            equity_index.append(ts)
            equity_values.append(portfolio.equity(c))

        if current_side != 0 and portfolio.position != 0.0:
            last_close = float(closes[-1])
            exit_side = -current_side
            exit_price = self._exec_price(last_close, exit_side)
            notional = exit_price * abs(portfolio.position)
            fee = self._fee(notional)
            pnl_per_unit = (exit_price - portfolio.avg_entry) * current_side
            pnl = pnl_per_unit * abs(portfolio.position) - fee
            portfolio.cash += portfolio.position * exit_price - fee
            portfolio.fees_total += fee
            assert portfolio.last_entry_time is not None
            portfolio.trades.append(
                Trade(
                    entry_time=portfolio.last_entry_time,
                    exit_time=ts_index[-1],
                    side=current_side,
                    entry_price=portfolio.avg_entry,
                    exit_price=exit_price,
                    size=abs(portfolio.position),
                    fees_paid=fee,
                    pnl=pnl,
                )
            )
            portfolio.position = 0.0
            equity_values[-1] = portfolio.cash

        equity_curve = pd.Series(equity_values, index=pd.DatetimeIndex(equity_index), name="equity")

        rets = equity_curve.pct_change().fillna(0.0)
        metrics = PerformanceMetrics(bars_per_year=self.bars_per_year).compute(
            equity_curve=equity_curve,
            returns=rets,
            trades=portfolio.trades,
        )

        return BacktestResult(
            equity_curve=equity_curve,
            trades=portfolio.trades,
            metrics=metrics,
            signals=signals,
            df=df,
            initial_cash=self.initial_cash,
            fee_bps=self._effective_fee_bps(),
            slippage_bps=self._effective_slippage_bps(),
        )


__all__ = ["BacktestEngine", "BacktestResult"]

_ = np
