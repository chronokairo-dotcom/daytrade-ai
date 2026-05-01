"""LiveBroker stub.

This file intentionally does NOT implement real-money order placement.
It exists only as a placeholder so the architecture is clear.

Activating live trading would require:
  1. Explicit user opt-in via a future ``--enable-live-trading`` flag that
     does NOT yet exist on the CLI.
  2. A separate, audited code path (not this stub).
  3. Strict per-trade risk limits, kill switch, and exchange whitelist.

Until all three exist, instantiating or using this class raises
``NotImplementedError``. Do not "just remove the raise".
"""

from __future__ import annotations

from typing import Any, NoReturn


class LiveBroker:
    """Placeholder for a future live broker. Refuses to do anything."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._refuse()

    @staticmethod
    def _refuse() -> NoReturn:
        raise NotImplementedError(
            "LiveBroker is intentionally not implemented. Day-trade-ai is paper-trading "
            "only. Enabling live trading requires explicit user opt-in via a future "
            "--enable-live-trading flag (which does not yet exist), plus a separate "
            "audited implementation path. See REALITY-CHECK.md."
        )

    def market_order(self, *args: Any, **kwargs: Any) -> NoReturn:  # pragma: no cover - guard
        self._refuse()

    def target_position(self, *args: Any, **kwargs: Any) -> NoReturn:  # pragma: no cover - guard
        self._refuse()
