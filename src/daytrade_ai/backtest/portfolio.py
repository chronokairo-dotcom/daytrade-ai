"""Position + trade tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Trade:
    """A round-trip trade (entry + exit)."""

    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: int  # +1 long, -1 short
    entry_price: float
    exit_price: float
    size: float  # units of base asset
    fees_paid: float
    pnl: float

    @property
    def return_pct(self) -> float:
        denom = self.entry_price * self.size
        return self.pnl / denom if denom else 0.0


@dataclass
class Portfolio:
    """Mutable portfolio state used during a backtest pass."""

    initial_cash: float
    cash: float = 0.0
    position: float = 0.0  # signed units of base asset
    avg_entry: float = 0.0
    last_entry_time: pd.Timestamp | None = None
    fees_total: float = 0.0
    trades: list[Trade] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.cash == 0.0:
            self.cash = self.initial_cash

    def equity(self, mark_price: float) -> float:
        return self.cash + self.position * mark_price
