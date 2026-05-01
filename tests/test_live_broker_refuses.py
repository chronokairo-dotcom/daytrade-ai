from __future__ import annotations

import pytest

from daytrade_ai.paper.live_broker import LiveBroker


def test_live_broker_refuses_to_instantiate() -> None:
    with pytest.raises(NotImplementedError):
        LiveBroker()
