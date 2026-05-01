"""RSI mean-reversion: long when oversold, exit when neutral."""

from __future__ import annotations

import numpy as np
import pandas as pd

from daytrade_ai.strategies.base import Strategy, register


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


@register("rsi_mean_reversion")
class RSIMeanReversion(Strategy):
    """Long when RSI < oversold, exit when RSI > exit_above."""

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        exit_above: float = 55.0,
    ) -> None:
        self.period = period
        self.oversold = oversold
        self.exit_above = exit_above

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi_vals = rsi(df["close"], self.period)
        out: list[int] = []
        position = 0
        for val in rsi_vals.to_numpy(dtype=float):
            if np.isnan(val):
                out.append(0)
                continue
            if position == 0 and val < self.oversold:
                position = 1
            elif position == 1 and val > self.exit_above:
                position = 0
            out.append(position)
        return pd.Series(out, index=df.index, dtype="int64", name="signal")
