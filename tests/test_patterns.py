"""Tests for daytrade_ai.analysis.patterns."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from daytrade_ai.analysis.patterns import (
    PatternReport,
    analyze_patterns,
    render_markdown,
)


def _synth_df(n: int = 400, *, trend: float = 0.0, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1.0, size=n)
    base = 100.0 + np.cumsum(noise) + trend * np.arange(n)
    high = base + np.abs(rng.normal(0, 0.5, n))
    low = base - np.abs(rng.normal(0, 0.5, n))
    open_ = base + rng.normal(0, 0.2, n)
    close = base + rng.normal(0, 0.2, n)
    vol = rng.uniform(100, 1000, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx
    )


def test_analyze_returns_report() -> None:
    df = _synth_df()
    rep = analyze_patterns(df, symbol="TEST/USDT", timeframe="1h")
    assert isinstance(rep, PatternReport)
    assert rep.bars == len(df)
    assert rep.symbol == "TEST/USDT"
    assert rep.adx_bucket in {"chop", "trend", "strong-trend"}
    assert rep.trend_regime in {"uptrend", "downtrend", "neutral"}
    assert rep.atr_percentile_bucket in {"low", "mid", "high"}
    assert 0.0 <= rep.rsi_14 <= 100.0


def test_uptrend_detected() -> None:
    df = _synth_df(n=500, trend=0.5)  # strong positive drift
    rep = analyze_patterns(df, symbol="UP/USDT", timeframe="1h")
    assert rep.trend_regime == "uptrend"
    assert rep.sma_fast > rep.sma_slow


def test_downtrend_detected() -> None:
    df = _synth_df(n=500, trend=-0.5)
    rep = analyze_patterns(df, symbol="DN/USDT", timeframe="1h")
    assert rep.trend_regime == "downtrend"
    assert rep.sma_fast < rep.sma_slow


def test_render_markdown_contains_sections() -> None:
    df = _synth_df()
    rep = analyze_patterns(df, symbol="X/USDT", timeframe="1h")
    md = render_markdown(rep)
    for section in (
        "## Trend",
        "## Volatility",
        "## Momentum",
        "## Mean reversion",
        "## Range",
        "## Candles",
    ):
        assert section in md
    assert "X/USDT" in md


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        analyze_patterns(pd.DataFrame(columns=["open", "high", "low", "close"]))


def test_missing_columns_raises() -> None:
    df = pd.DataFrame({"open": [1.0], "high": [1.0], "low": [1.0]})
    with pytest.raises(ValueError):
        analyze_patterns(df)
