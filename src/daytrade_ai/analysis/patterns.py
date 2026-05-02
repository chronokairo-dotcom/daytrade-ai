"""Structured pattern analysis on OHLCV dataframes.

Pure pandas/numpy implementation. No ta-lib, no external indicator libraries.
Designed to be fast (vectorized where possible), deterministic, and testable
on small synthetic fixtures.

The output is a :class:`PatternReport` dataclass that aggregates:

- Trend regime (50/200 SMA + ADX bucket)
- Volatility regime (ATR percentile + realized vol)
- Momentum (RSI(14) current value + zone counts over last N bars)
- Mean reversion signals (bollinger %b, z-score vs 20-bar SMA)
- Range stats (% time inside Donchian(20), breakout frequency)
- Recent candle classification counts (doji / hammer / engulfing) on last 14 bars
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Indicator helpers (pure pandas / numpy)
# ---------------------------------------------------------------------------


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    # Wilder smoothing approximated with ewm alpha=1/n.
    avg_up = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    avg_down = down.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = avg_up / avg_down.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = _true_range(df)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder's ADX. Returns a Series the same length as df (NaN warmup)."""
    high = df["high"]
    low = df["low"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move.clip(lower=0.0)
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move.clip(lower=0.0)
    tr = _true_range(df)
    atr = tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean() / atr
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return adx


# ---------------------------------------------------------------------------
# Candle pattern detection (basic, no ta-lib)
# ---------------------------------------------------------------------------


def _classify_candles(df: pd.DataFrame) -> pd.DataFrame:
    """Return a dataframe with boolean flags doji/hammer/bullish_engulfing/bearish_engulfing."""
    o = df["open"]
    h = df["high"]
    l = df["low"]  # noqa: E741
    c = df["close"]

    body = (c - o).abs()
    rng = (h - l).replace(0.0, np.nan)
    upper_wick = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_wick = pd.concat([c, o], axis=1).min(axis=1) - l

    doji = (body / rng) < 0.1

    # Hammer: small body at top of range, long lower wick.
    hammer = (body / rng < 0.35) & (lower_wick / rng > 0.5) & (upper_wick / rng < 0.2)

    prev_o = o.shift(1)
    prev_c = c.shift(1)
    prev_body = (prev_c - prev_o).abs()

    bull_engulf = (
        (prev_c < prev_o)  # prev red
        & (c > o)  # cur green
        & (c >= prev_o)
        & (o <= prev_c)
        & (body > prev_body)
    )
    bear_engulf = (prev_c > prev_o) & (c < o) & (c <= prev_o) & (o >= prev_c) & (body > prev_body)

    return pd.DataFrame(
        {
            "doji": doji.fillna(False),
            "hammer": hammer.fillna(False),
            "bull_engulfing": bull_engulf.fillna(False),
            "bear_engulfing": bear_engulf.fillna(False),
        },
        index=df.index,
    )


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class PatternReport:
    symbol: str
    timeframe: str
    bars: int
    start: str
    end: str
    last_close: float

    trend_regime: str  # "uptrend" | "downtrend" | "neutral"
    adx_bucket: str  # "chop" | "trend" | "strong-trend"
    adx_value: float
    sma_fast: float
    sma_slow: float

    atr_pct_of_price: float
    atr_percentile_bucket: str  # "low" | "mid" | "high"
    realized_vol_30: float

    rsi_14: float
    rsi_overbought_count_200: int
    rsi_oversold_count_200: int
    rsi_neutral_count_200: int

    bbands_pct_b: float  # 0..1 ish, distance within bands
    zscore_close_sma20: float

    pct_time_in_donchian20: float
    breakout_count_200: int

    candle_doji_14: int
    candle_hammer_14: int
    candle_bull_engulf_14: int
    candle_bear_engulf_14: int

    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def analyze_patterns(
    df: pd.DataFrame,
    *,
    symbol: str = "asset",
    timeframe: str = "1h",
) -> PatternReport:
    """Compute a :class:`PatternReport` from an OHLCV dataframe.

    Requires columns: open, high, low, close, volume. Index expected to be
    a DatetimeIndex but not strictly required.
    """
    if df.empty:
        raise ValueError("Cannot analyze empty dataframe")

    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    n = len(df)
    close = df["close"].astype(float)

    sma50 = _sma(close, 50)
    sma200 = _sma(close, 200)
    last_sma50 = float(sma50.iloc[-1]) if not np.isnan(sma50.iloc[-1]) else float(close.iloc[-1])
    last_sma200 = float(sma200.iloc[-1]) if not np.isnan(sma200.iloc[-1]) else float(close.iloc[-1])
    if last_sma50 > last_sma200 * 1.005:
        trend = "uptrend"
    elif last_sma50 < last_sma200 * 0.995:
        trend = "downtrend"
    else:
        trend = "neutral"

    adx_series = _adx(df, 14)
    adx_val = float(adx_series.iloc[-1]) if not np.isnan(adx_series.iloc[-1]) else 0.0
    if adx_val < 20:
        adx_bucket = "chop"
    elif adx_val < 40:
        adx_bucket = "trend"
    else:
        adx_bucket = "strong-trend"

    # Volatility
    atr_series = _atr(df, 14)
    last_atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else 0.0
    last_close = float(close.iloc[-1])
    atr_pct = last_atr / last_close if last_close else 0.0

    atr_clean = atr_series.dropna()
    if not atr_clean.empty and last_atr > 0:
        atr_rank = float((atr_clean <= last_atr).mean())
    else:
        atr_rank = 0.5
    if atr_rank < 0.33:
        atr_bucket = "low"
    elif atr_rank < 0.66:
        atr_bucket = "mid"
    else:
        atr_bucket = "high"

    rets = close.pct_change()
    rv_30 = float(rets.tail(30).std() * np.sqrt(30)) if len(rets) >= 5 else 0.0

    # Momentum
    rsi = _rsi(close, 14)
    rsi_last = float(rsi.iloc[-1])
    last_window = rsi.tail(min(200, n))
    overbought = int((last_window >= 70).sum())
    oversold = int((last_window <= 30).sum())
    neutral = int(((last_window > 30) & (last_window < 70)).sum())

    # Mean reversion: BBands %b, z-score
    sma20 = _sma(close, 20)
    std20 = close.rolling(20, min_periods=20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    bb_pct_b = (close - lower) / (upper - lower).replace(0.0, np.nan)
    pct_b_last = float(bb_pct_b.iloc[-1]) if not np.isnan(bb_pct_b.iloc[-1]) else 0.5

    z = (close - sma20) / std20.replace(0.0, np.nan)
    z_last = float(z.iloc[-1]) if not np.isnan(z.iloc[-1]) else 0.0

    # Range stats: Donchian(20)
    don_high = df["high"].rolling(20, min_periods=20).max()
    don_low = df["low"].rolling(20, min_periods=20).min()
    inside = ((close <= don_high) & (close >= don_low)).astype(float)
    pct_inside = float(inside.dropna().mean()) if inside.dropna().size > 0 else 0.0

    breakout_up = (close > don_high.shift(1)).astype(int)
    breakout_dn = (close < don_low.shift(1)).astype(int)
    breakouts = (breakout_up + breakout_dn).tail(min(200, n))
    breakout_count = int(breakouts.sum())

    # Candles on last 14 bars
    candles = _classify_candles(df).tail(14)
    notes: list[str] = []
    if rsi_last >= 70:
        notes.append("RSI overbought (>=70).")
    elif rsi_last <= 30:
        notes.append("RSI oversold (<=30).")
    if abs(z_last) >= 2:
        notes.append(f"Close is {z_last:+.2f}σ from 20-bar SMA — extended.")
    if adx_bucket == "chop":
        notes.append("ADX < 20: market is choppy / range-bound; trend strategies likely to bleed.")

    start = str(df.index[0]) if isinstance(df.index, pd.DatetimeIndex) else "0"
    end = str(df.index[-1]) if isinstance(df.index, pd.DatetimeIndex) else str(n - 1)

    return PatternReport(
        symbol=symbol,
        timeframe=timeframe,
        bars=n,
        start=start,
        end=end,
        last_close=last_close,
        trend_regime=trend,
        adx_bucket=adx_bucket,
        adx_value=adx_val,
        sma_fast=last_sma50,
        sma_slow=last_sma200,
        atr_pct_of_price=atr_pct,
        atr_percentile_bucket=atr_bucket,
        realized_vol_30=rv_30,
        rsi_14=rsi_last,
        rsi_overbought_count_200=overbought,
        rsi_oversold_count_200=oversold,
        rsi_neutral_count_200=neutral,
        bbands_pct_b=pct_b_last,
        zscore_close_sma20=z_last,
        pct_time_in_donchian20=pct_inside,
        breakout_count_200=int(breakout_count),
        candle_doji_14=int(candles["doji"].sum()),
        candle_hammer_14=int(candles["hammer"].sum()),
        candle_bull_engulf_14=int(candles["bull_engulfing"].sum()),
        candle_bear_engulf_14=int(candles["bear_engulfing"].sum()),
        notes=notes,
    )


def render_markdown(rep: PatternReport, *, generated_at: datetime | None = None) -> str:
    """Render a :class:`PatternReport` as a markdown string."""
    ts = generated_at.isoformat() if generated_at else "n/a"
    lines: list[str] = [
        f"# Pattern report :: {rep.symbol} :: {rep.timeframe}",
        "",
        f"_generated: {ts}_",
        "",
        f"- bars: **{rep.bars}**",
        f"- range: {rep.start} → {rep.end}",
        f"- last close: **{rep.last_close:.4f}**",
        "",
        "## Trend",
        "",
        f"- regime: **{rep.trend_regime}**",
        f"- SMA50: {rep.sma_fast:.4f}",
        f"- SMA200: {rep.sma_slow:.4f}",
        f"- ADX(14): {rep.adx_value:.2f} → **{rep.adx_bucket}**",
        "",
        "## Volatility",
        "",
        f"- ATR(14) / price: {rep.atr_pct_of_price * 100:.2f}%",
        f"- ATR percentile bucket: **{rep.atr_percentile_bucket}**",
        f"- realized vol (30 bars): {rep.realized_vol_30:.4f}",
        "",
        "## Momentum",
        "",
        f"- RSI(14): **{rep.rsi_14:.2f}**",
        f"- last 200 bars: overbought={rep.rsi_overbought_count_200} "
        f"oversold={rep.rsi_oversold_count_200} neutral={rep.rsi_neutral_count_200}",
        "",
        "## Mean reversion",
        "",
        f"- Bollinger %b: {rep.bbands_pct_b:.3f}",
        f"- z-score vs SMA20: {rep.zscore_close_sma20:+.2f}",
        "",
        "## Range",
        "",
        f"- % time inside Donchian(20): {rep.pct_time_in_donchian20 * 100:.1f}%",
        f"- breakouts (last 200 bars): {rep.breakout_count_200}",
        "",
        "## Candles (last 14)",
        "",
        f"- doji: {rep.candle_doji_14}",
        f"- hammer: {rep.candle_hammer_14}",
        f"- bullish engulfing: {rep.candle_bull_engulf_14}",
        f"- bearish engulfing: {rep.candle_bear_engulf_14}",
        "",
        "## Notes",
        "",
    ]
    if rep.notes:
        lines.extend(f"- {n}" for n in rep.notes)
    else:
        lines.append("- (no remarkable signals)")
    lines.append("")
    return "\n".join(lines)
