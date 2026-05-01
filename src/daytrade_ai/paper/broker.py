"""PaperBroker: simulates fills against live ccxt prices. Never sends orders."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class Fill:
    timestamp: datetime
    symbol: str
    side: int  # +1 long, -1 short / sell
    price: float
    size: float
    fee: float


@dataclass
class PaperBroker:
    """Simulated broker. Fills market orders at the provided reference price
    plus configurable slippage. No network calls. No real money. Ever."""

    symbol: str
    initial_cash: float = 10_000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0

    cash: float = 0.0
    position: float = 0.0
    fills: list[Fill] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.cash == 0.0:
            self.cash = self.initial_cash
        logger.info(
            "PaperBroker initialised | symbol=%s cash=%.2f fee_bps=%.1f slippage_bps=%.1f",
            self.symbol,
            self.cash,
            self.fee_bps,
            self.slippage_bps,
        )

    # ------------------------------------------------------------------
    def _exec_price(self, ref_price: float, side: int) -> float:
        slip = self.slippage_bps / 10_000.0
        return ref_price * (1.0 + slip) if side > 0 else ref_price * (1.0 - slip)

    def _fee(self, notional: float) -> float:
        return abs(notional) * (self.fee_bps / 10_000.0)

    # ------------------------------------------------------------------
    def market_order(
        self,
        side: int,
        size: float,
        ref_price: float,
        timestamp: datetime | None = None,
    ) -> Fill:
        """Simulate a market fill at ref_price ± slippage. Returns the Fill."""
        if side not in (-1, 1):
            raise ValueError("side must be -1 or +1")
        if size <= 0:
            raise ValueError("size must be > 0")
        ts = timestamp or datetime.now(tz=UTC)
        price = self._exec_price(ref_price, side)
        notional = price * size
        fee = self._fee(notional)
        self.cash -= side * notional + fee
        self.position += side * size
        fill = Fill(timestamp=ts, symbol=self.symbol, side=side, price=price, size=size, fee=fee)
        self.fills.append(fill)
        logger.info(
            "PAPER FILL | %s %s size=%.6f price=%.4f fee=%.4f cash=%.2f position=%.6f",
            "BUY" if side > 0 else "SELL",
            self.symbol,
            size,
            price,
            fee,
            self.cash,
            self.position,
        )
        return fill

    def equity(self, mark_price: float) -> float:
        return self.cash + self.position * mark_price

    def target_position(self, target_units: float, ref_price: float) -> Fill | None:
        """Move position toward `target_units`. Returns the fill if any."""
        delta = target_units - self.position
        if abs(delta) < 1e-12:
            return None
        side = 1 if delta > 0 else -1
        return self.market_order(side=side, size=abs(delta), ref_price=ref_price)
