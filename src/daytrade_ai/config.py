"""Pydantic settings loaded from environment + .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config. All paper-trading-safe defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DAYTRADE_",
        extra="ignore",
    )

    exchange: str = "binance"
    api_key: str = ""
    api_secret: str = ""

    cache_dir: Path = Field(default=Path("data/cache"))

    default_symbol: str = "BTC/USDT"
    default_timeframe: str = "1h"

    fee_bps: float = 10.0  # 0.10% per side
    slippage_bps: float = 5.0  # 0.05% per fill
    initial_cash: float = 10_000.0

    # Hard kill switch. Even if someone wires a LiveBroker, this must remain false.
    enable_live_trading: bool = False


def get_settings() -> Settings:
    """Construct settings (re-read .env each call so tests can override)."""
    return Settings()
