"""Buy-and-hold benchmark strategy: always long."""

from __future__ import annotations

import pandas as pd

from daytrade_ai.strategies.base import Strategy, register


@register("buy_and_hold")
class BuyAndHold(Strategy):
    """Always long. This is the benchmark every strategy must beat."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(1, index=df.index, dtype="int64", name="signal")
