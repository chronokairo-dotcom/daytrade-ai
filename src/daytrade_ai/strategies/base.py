"""Strategy ABC + registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import ClassVar

import pandas as pd

registry: dict[str, type[Strategy]] = {}


def register(name: str) -> Callable[[type[Strategy]], type[Strategy]]:
    """Decorator to register a Strategy subclass under ``name``."""

    def _wrap(cls: type[Strategy]) -> type[Strategy]:
        if name in registry:
            raise ValueError(f"Strategy '{name}' already registered")
        cls.name = name
        registry[name] = cls
        return cls

    return _wrap


class Strategy(ABC):
    """Base strategy. Implementations return signals in {-1, 0, 1}.

    Convention: a signal at bar t is acted on at the OPEN of bar t+1
    (the engine handles that shift to avoid lookahead bias).
    """

    name: ClassVar[str] = "base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return Series indexed identically to df, values in {-1, 0, 1}."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Strategy {self.name}>"
