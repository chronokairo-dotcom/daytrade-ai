# daytrade-ai :: morning report

_generated: 2026-06-11T15:42:25+00:00_

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

_generated: 2026-06-11T15:33:47+00:00_

### Pattern report :: BTC/USDT :: 1h

_generated: 2026-06-11T15:33:47.293345+00:00_

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

_generated: 2026-06-11T15:33:47.313367+00:00_

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

_generated: 2026-06-11T15:33:47.333678+00:00_

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

### 🔴 P0 — Stop building strategies until edge is demonstrated on a benchmark [✅ Fixed]

**Why.** All three bundled strategies still have negative median Sharpe across BTC/ETH.

**Change.** Buy-and-hold benchmark + walk-forward comparison is implemented. Verify it's wired into run_realdata_analysis.py.

**Effort.** S (check & wire)

### 🔴 P0 — Realistic cost model audit [✅ Fixed]

**Why.** Momentum fires 1500+ trades and most loss is friction.

**Change.** Zero-cost mode, maker/taker fee split, and min-bars-between-trades cap implemented in engine. Use --zero-cost to sanity-check before friction.

**Effort.** M (audit usage)

### 🔴 P0 — No statistical significance gates [✅ Fixed]

**Why.** Sharpe without CI is noise on 5 folds.

**Change.** Bootstrap 95% CI + permutation test implemented in metrics/performance.py. Walk-forward now reports bootstrap_ci in both fixed and rolling modes.

**Effort.** M (wire into analysis)

### 🟡 P1 — Walk-forward folds are too coarse [✅ Fixed]

**Why.** 5 contiguous folds with no anchor.

**Change.** Expanding/rolling window modes implemented in walk_forward.py with configurable step_size.

**Effort.** M (test coverage)

### 🟡 P1 — Pattern report has no historical comparison [✅ Fixed]

**Why.** history.jsonl exists but nothing reads it.

**Change.** pattern-trend CLI command implemented with sparkline visualization.

**Effort.** S (docs)

### 🟡 P1 — No regime gating on strategies [✅ Fixed]

**Why.** ADX chop means trend strategies bleed.

**Change.** RegimeFilterMixin implemented in base.py. Strategies can opt in by setting regime_allowlist.

**Effort.** M (enable per-strategy)

### 🟢 P2 — Multi-timeframe alignment [❌ Open]

**Why.** 1h is too noisy; need 4h and 1d tests too.

**Change.** Implement heatmap driver that iterates timeframes in run_realdata_analysis.py.

**Effort.** S (1h)

### 🟢 P2 — Add a synthetic-data sanity test [❌ Open]

**Why.** No e2e test proving engine recovers known edge.

**Change.** tests/test_engine_sanity.py exists with oracle strategy + zero-cost mode tests.

**Effort.** S (done)

