"""Strategy registry. Importing this module also imports built-in strategies
so they self-register via the @register decorator."""

from __future__ import annotations

# Side-effect imports to populate registry.
from daytrade_ai.strategies import momentum, rsi_mean_reversion, sma_cross  # noqa: F401
from daytrade_ai.strategies.base import Strategy, register, registry

__all__ = ["Strategy", "get_strategy", "list_strategies", "register", "registry"]


def list_strategies() -> list[str]:
    return sorted(registry.keys())


def get_strategy(name: str, **params: object) -> Strategy:
    if name not in registry:
        raise KeyError(f"Unknown strategy '{name}'. Available: {list_strategies()}")
    return registry[name](**params)
