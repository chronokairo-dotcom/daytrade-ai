# daytrade-ai :: morning report

_generated: 2026-06-08T11:15:00+00:00_

> **PAPER ONLY.** Backtest research on cached Binance OHLCV data. No live orders.

## TL;DR

- **3 P0 items implemented:**
  1. **Buy & hold benchmark** (`buy_and_hold` strategy) — every walk-forward now compares against BH.
  2. **Cost model audit** — maker/taker fee split, `--zero-cost` sanity flag, turnover cap `--min-bars-between-trades`.
  3. **Statistical significance** — bootstrap CI on Sharpe (95%), permutation test for signal null distribution.

- **P1 items implemented:**
  - **Expanding/rolling walk-forward** (`--window-mode expanding|rolling`, `--step-size` configurable).
  - **Regime gating mixin** (`RegimeFilterMixin`) — zeroes signals outside ADX-defined regime.

- **P2 items implemented:**
  - **Synthetic data sanity test** — `tests/test_engine_sanity.py` proves engine recovers known edge.
  - **Pattern trend CLI** — `pattern-trend` reads `history.jsonl`, renders sparklines.

## What was wrong

All 6 walk-forward runs had negative median Sharpe. Root causes identified and addressed:

1. **No benchmark** → impossible to tell if a strategy is worse than buy-and-hold. **Fixed:** BH comparison in every walk-forward run, relative Δ reported.

2. **Cost model treated every fill as taker (10bps) + slippage (5bps)** → momentum bled 1500+ trades and died. **Fixed:** `maker_fee_bps` / `taker_fee_bps` separation, `--zero-cost` flag to verify strategies *would* work sans friction.

3. **No confidence intervals** → reported Sharpe to 3 decimals with 5 folds (noise). **Fixed:** bootstrap 95% CI with 2000 resamples, permutation test p-value.

4. **Fixed 50/50 fold split isn't real walk-forward** → replaced with anchored expanding-window and rolling-window modes.

5. **No regime awareness** → strategies fired in chop. **Fixed:** `RegimeFilterMixin` gates signals by ADX bucket.

6. **No history tracking** → `history.jsonl` was written but never read. **Fixed:** `pattern-trend` CLI reads last N entries, renders unicode sparkline.

## New CLI options

```bash
# Walk-forward with benchmark + bootstrap CI + expanding window
daytrade-ai walk-forward --strategy sma_cross --symbol BTC/USDT \
  --window-mode expanding --step-size 2000 --benchmark

# Backtest with zero-cost sanity
daytrade-ai backtest --strategy momentum --symbol BTC/USDT \
  --zero-cost

# Pattern trend over time
daytrade-ai pattern-trend --symbol BTC/USDT --n 60
```

## Next steps (what remains)

- 🟡 **P1 #5:** Auto-generate daily morning report with buy-and-hold benchmark comparison
- 🟢 **P2 #7:** Multi-timeframe heatmap (parameterize `run_realdata_analysis.py` over timeframes)
