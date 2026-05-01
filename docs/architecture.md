# Architecture

```
            +--------------+
            |   data/      |  CSV / ccxt OHLCV → pandas.DataFrame (UTC)
            +------+-------+
                   |
                   v
           +-------+--------+
           | strategies/   |  generate_signals(df) -> Series in {-1, 0, 1}
           +-------+-------+
                   |
                   v
           +-------+--------+
           |  backtest/    |  vectorized loop, fees + slippage,
           |   engine      |  trade tracking, equity curve
           +-------+-------+
                   |
                   v
           +-------+--------+
           |  metrics/     |  sharpe, sortino, calmar, max_dd, etc.
           +-------+-------+
                   |
                   v
           +-------+--------+
           |  reporting/   |  text + markdown reports, ascii equity
           +---------------+
```

## Key contracts

- **DataSource**: `fetch(symbol, timeframe, since, until) -> DataFrame`. Always
  validated via `DataSource.validate(df)` to be UTC-indexed with the canonical
  `open, high, low, close, volume` columns.
- **Strategy**: `generate_signals(df) -> Series[{-1, 0, 1}]`. The signal at bar
  *t* is acted on at the OPEN of bar *t+1* (the engine handles the shift).
- **BacktestEngine**: walks bar-by-bar; opens / closes positions with realistic
  cost modelling. Liquidates at the final close so equity is comparable.
- **WalkForward**: rolling N-fold split with a train/test ratio. For
  non-parametric strategies the "fit" stage is a sanity check.
- **PaperBroker**: simulates fills against a reference price. Never network.
- **LiveBroker**: stub. Refuses to instantiate. See `paper-trading.md`.

## Why a Python loop, not pure vectorization?

Vectorized PnL math is great for headline returns but it makes per-trade fee
accounting and avg-entry tracking awkward. We use a single O(n) Python loop
and an `O(1)`-per-bar `.iloc`-free path (pre-extracted numpy arrays) to keep
it fast enough for hundreds of thousands of bars.
