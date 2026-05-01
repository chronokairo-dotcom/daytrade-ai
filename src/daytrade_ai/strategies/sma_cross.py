"""Simple moving-average crossover."""

from __future__ import annotations

import numpy as np
import pandas as pd

from daytrade_ai.strategies.base import Strategy, register


@register("sma_cross")
class SMACross(Strategy):
    """Long when fast SMA > slow SMA, flat (or short) otherwise."""

    def __init__(self, fast: int = 10, slow: int = 30, allow_short: bool = False) -> None:
        if fast >= slow:
            raise ValueError("fast must be < slow")
        self.fast = fast
        self.slow = slow
        self.allow_short = allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        fast_ma = close.rolling(self.fast, min_periods=self.fast).mean()
        slow_ma = close.rolling(self.slow, min_periods=self.slow).mean()
        diff = fast_ma - slow_ma
        sig = np.where(diff > 0, 1, np.where(diff < 0, -1 if self.allow_short else 0, 0))
        return pd.Series(sig, index=df.index, dtype="int64", name="signal").fillna(0)
