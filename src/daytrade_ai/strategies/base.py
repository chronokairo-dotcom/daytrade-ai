from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import ClassVar

import pandas as pd

registry: dict[str, type[Strategy]] = {}


def register(name: str) -> Callable[[type[Strategy]], type[Strategy]]:
    def _wrap(cls: type[Strategy]) -> type[Strategy]:
        if name in registry:
            raise ValueError(f"Strategy '{name}' already registered")
        cls.name = name
        registry[name] = cls
        return cls

    return _wrap


class RegimeFilterMixin:
    def apply_regime_filter(
        self,
        signals: pd.Series,
        df: pd.DataFrame,
        adx_period: int = 14,
        adx_threshold: float = 20.0,
        allow_long_in_chop: bool = True,
        allow_long_in_trend: bool = True,
        allow_short_in_chop: bool = False,
        allow_short_in_trend: bool = True,
    ) -> pd.Series:
        from daytrade_ai.analysis.patterns import _adx

        adx_series = _adx(df, adx_period)
        regime = adx_series >= adx_threshold
        filtered = signals.copy()
        for i in range(len(signals)):
            if pd.isna(regime.iloc[i]) or not regime.iloc[i]:
                if (signals.iloc[i] == 1 and not allow_long_in_chop) or (
                    signals.iloc[i] == -1 and not allow_short_in_chop
                ):
                    filtered.iloc[i] = 0
            else:
                if (signals.iloc[i] == 1 and not allow_long_in_trend) or (
                    signals.iloc[i] == -1 and not allow_short_in_trend
                ):
                    filtered.iloc[i] = 0
        return filtered


class Strategy(ABC):
    name: ClassVar[str] = "base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        pass

    def __repr__(self) -> str:
        return f"<Strategy {self.name}>"
