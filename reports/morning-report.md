# daytrade-ai :: morning report

_generated: 2026-05-01T03:57:28+00:00_

> **PAPER ONLY.** This report describes research-grade backtests on cached
> Binance public OHLCV data. No live orders. No claims of profitability.

## TL;DR

- 6 (symbol × strategy) walk-forward runs completed.
- **0** had positive median Sharpe; **6** had negative or zero.
- **Verdict: no edge detected.** Every bundled strategy lost money on out-of-sample folds for both BTC/USDT and ETH/USDT.
- Recommendation: stop adding strategies until the engine, costs, and validation are audited. See P0 items below.

## Walk-forward results (5 folds, train_ratio=0.5)

| Symbol | Strategy | median Sharpe | mean ret | mean MaxDD | win folds |
|---|---|---:|---:|---:|---:|
| BTC/USDT | momentum | -2.887 | -30.37% | -34.41% | 0/5 |
| BTC/USDT | rsi_mean_reversion | -0.860 | -7.45% | -13.98% | 0/5 |
| BTC/USDT | sma_cross | -1.108 | -8.14% | -20.31% | 1/5 |
| ETH/USDT | momentum | -1.009 | -14.98% | -34.61% | 1/5 |
| ETH/USDT | rsi_mean_reversion | -0.167 | -8.60% | -21.38% | 1/5 |
| ETH/USDT | sma_cross | -0.499 | 5.31% | -24.81% | 2/5 |

## Full-range backtest (2023-01-01 → now)

| Symbol | Strategy | total return | Sharpe | MaxDD | trades |
|---|---|---:|---:|---:|---:|
| BTC/USDT | momentum | -96.97% | -3.007 | -97.91% | 1633 |
| BTC/USDT | rsi_mean_reversion | -39.73% | -0.502 | -43.82% | 178 |
| BTC/USDT | sma_cross | -62.56% | -0.735 | -74.97% | 595 |
| ETH/USDT | momentum | -96.29% | -2.126 | -97.77% | 1578 |
| ETH/USDT | rsi_mean_reversion | -54.32% | -0.500 | -68.27% | 185 |
| ETH/USDT | sma_cross | -76.08% | -0.807 | -83.52% | 593 |

## Latest pattern snapshot

### Pattern report :: latest snapshot

_generated: 2026-05-01T03:56:30+00:00_

### Pattern report :: BTC/USDT :: 1h

_generated: 2026-05-01T03:56:30.183536+00:00_

- bars: **720**
- range: 2026-04-01 04:00:00+00:00 → 2026-05-01 03:00:00+00:00
- last close: **77207.9900**

#### Trend

- regime: **downtrend**
- SMA50: 76385.6390
- SMA200: 77302.1925
- ADX(14): 16.29 → **chop**

#### Volatility

- ATR(14) / price: 0.48%
- ATR percentile bucket: **low**
- realized vol (30 bars): 0.0171

#### Momentum

- RSI(14): **67.44**
- last 200 bars: overbought=4 oversold=3 neutral=193

#### Mean reversion

- Bollinger %b: 1.293
- z-score vs SMA20: +3.17

#### Range

- % time inside Donchian(20): 97.4%
- breakouts (last 200 bars): 13

#### Candles (last 14)

- doji: 2
- hammer: 0
- bullish engulfing: 2
- bearish engulfing: 2

#### Notes

- Close is +3.17σ from 20-bar SMA — extended.
- ADX < 20: market is choppy / range-bound; trend strategies likely to bleed.


### Pattern report :: ETH/USDT :: 1h

_generated: 2026-05-01T03:56:30.203751+00:00_

- bars: **720**
- range: 2026-04-01 04:00:00+00:00 → 2026-05-01 03:00:00+00:00
- last close: **2284.6600**

#### Trend

- regime: **downtrend**
- SMA50: 2274.5928
- SMA200: 2309.3102
- ADX(14): 13.77 → **chop**

#### Volatility

- ATR(14) / price: 0.60%
- ATR percentile bucket: **low**
- realized vol (30 bars): 0.0208

#### Momentum

- RSI(14): **62.61**
- last 200 bars: overbought=11 oversold=4 neutral=185

#### Mean reversion

- Bollinger %b: 1.360
- z-score vs SMA20: +3.44

#### Range

- % time inside Donchian(20): 97.4%
- breakouts (last 200 bars): 14

#### Candles (last 14)

- doji: 1
- hammer: 0
- bullish engulfing: 3
- bearish engulfing: 2

#### Notes

- Close is +3.44σ from 20-bar SMA — extended.
- ADX < 20: market is choppy / range-bound; trend strategies likely to bleed.


### Pattern report :: SOL/USDT :: 1h

_generated: 2026-05-01T03:56:30.223073+00:00_

- bars: **720**
- range: 2026-04-01 04:00:00+00:00 → 2026-05-01 03:00:00+00:00
- last close: **83.9700**

#### Trend

- regime: **downtrend**
- SMA50: 83.4848
- SMA200: 85.1329
- ADX(14): 19.52 → **chop**

#### Volatility

- ATR(14) / price: 0.57%
- ATR percentile bucket: **low**
- realized vol (30 bars): 0.0198

#### Momentum

- RSI(14): **64.03**
- last 200 bars: overbought=2 oversold=4 neutral=194

#### Mean reversion

- Bollinger %b: 1.214
- z-score vs SMA20: +2.86

#### Range

- % time inside Donchian(20): 97.4%
- breakouts (last 200 bars): 16

#### Candles (last 14)

- doji: 5
- hammer: 0
- bullish engulfing: 2
- bearish engulfing: 2

#### Notes

- Close is +2.86σ from 20-bar SMA — extended.
- ADX < 20: market is choppy / range-bound; trend strategies likely to bleed.

## Urgent changes

### 🔴 P0 — Stop building strategies until edge is demonstrated on a benchmark

**Why.** All three bundled strategies have negative median Sharpe on both BTC/USDT and ETH/USDT walk-forward (1h, 2023→2026). Adding more strategies without first proving the engine + cost model can find any positive baseline is research theatre.

**Change.** Add a buy-and-hold benchmark in `src/daytrade_ai/strategies/buy_and_hold.py` and a relative-performance column in walk-forward summaries (`backtest/walk_forward.py`).

**Effort.** S (1–2h)

### 🔴 P0 — Realistic cost model audit: 10 bps fee + 5 bps slippage on 1h is borderline insane

**Why.** Momentum strategy fires 1500+ trades over the test window and dies — most of the loss is friction. The defaults assume retail Binance maker fees, but every fill is treated as a taker with directional slippage. This biases all conclusions.

**Change.** In `backtest/engine.py` separate maker/taker fee, model partial fills (or at least cap turnover per bar). Add a `--zero-cost` sanity-check flag to the CLI to confirm strategies *would* be profitable before friction.

**Effort.** M (3–5h)

### 🔴 P0 — No statistical significance gates

**Why.** We report Sharpe to 3 decimal places without any confidence interval. On 5 folds that's noise. There is no way to distinguish 'bad strategy' from 'unlucky strategy' as currently reported.

**Change.** Add bootstrap confidence intervals to `metrics/performance.py` and a permutation test that shuffles signals to estimate the null distribution. Refuse to declare 'edge' unless median Sharpe > 95th percentile of null.

**Effort.** M (4–6h)

### 🟡 P1 — Walk-forward folds are too coarse and overlap nothing

**Why.** Current implementation uses 5 contiguous folds with a 50/50 train/test split *within each fold*. That's not really walk-forward — it's 5 independent in-sample/out-of-sample splits with no anchor.

**Change.** Refactor `backtest/walk_forward.py` to support anchored expanding-window or rolling-window walk-forward with a configurable step size.

**Effort.** M (3–4h)

### 🟡 P1 — Pattern report has no historical comparison

**Why.** `reports/patterns/latest.md` is a snapshot. We persist `history.jsonl` but nothing reads it. Regime changes are invisible.

**Change.** Add a `pattern-trend` CLI that plots ATR percentile, RSI, and ADX over the last N passes from `history.jsonl`. Markdown sparkline / ascii is fine.

**Effort.** S (2h)

### 🟡 P1 — No regime gating on strategies

**Why.** Latest pattern snapshot shows ADX in the 13–20 range across BTC/ETH/SOL (chop). SMA cross and momentum should be disabled in chop; RSI mean-revert should only fire then. The strategies don't read the regime at all.

**Change.** Add an optional `regime_filter` mixin that consults a `PatternReport` and zeros signals outside the appropriate regime bucket.

**Effort.** M (3h)

### 🟢 P2 — Multi-timeframe alignment

**Why.** 1h is too noisy for trend-following with these defaults. Should at least test 4h and 1d before declaring strategies dead.

**Change.** Run `scripts/run_realdata_analysis.py` parameterized over a list of timeframes; cache and emit a heatmap markdown table.

**Effort.** S (1h)

### 🟢 P2 — Add a synthetic-data sanity test

**Why.** We have no end-to-end test that proves the engine recovers a known edge from a deterministic series (e.g. perfect oracle signal → near-100% return).

**Change.** Add `tests/test_engine_sanity.py` that constructs a sine wave + an oracle strategy and asserts the engine yields >> 0 Sharpe.

**Effort.** S (1h)

