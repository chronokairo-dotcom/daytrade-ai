"""Momentum: long when N-period return > threshold."""

from __future__ import annotations

import numpy as np
import pandas as pd

from daytrade_ai.strategies.base import Strategy, register


@register("momentum")
class Momentum(Strategy):
    """Long when rolling lookback return exceeds threshold."""

    def __init__(self, lookback: int = 20, threshold: float = 0.0) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        self.lookback = lookback
        self.threshold = threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        ret = close.pct_change(self.lookback)
        sig = np.where(ret > self.threshold, 1, 0)
        return pd.Series(sig, index=df.index, dtype="int64", name="signal").fillna(0)
