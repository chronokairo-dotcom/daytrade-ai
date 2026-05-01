# Paper trading (and how NOT to run live)

## TL;DR

This project is **paper trading only**. There is no live order path.

## Run a paper session

```bash
daytrade-ai paper --strategy sma_cross --symbol BTC/USDT --timeframe 1h
```

What happens:

1. Each iteration, latest OHLCV is fetched from your configured exchange
   (read-only — public market data, no API keys required for most spot pairs).
2. The strategy produces a signal on the latest bar.
3. `PaperBroker` simulates a market fill at the close price plus configured
   slippage and applies a fee.
4. Cash, position, and fills are logged. **Nothing leaves the machine.**

You can stop the loop with `Ctrl-C` at any time.

## Why there is no live trading

Read [REALITY-CHECK.md](../REALITY-CHECK.md). The short version: ~91% of
retail day traders lose money. We will not enable a one-flag-flip path to
real-money execution from a research repo.

## What about `LiveBroker`?

`src/daytrade_ai/paper/live_broker.py` exists as a placeholder. It raises
`NotImplementedError` on instantiation. The CLI also refuses
`--enable-live-trading` at the argument-parser level. Both safety layers are
intentional. To enable real live trading you would need to:

1. Add an audited live execution path in a separate module.
2. Add a real `--enable-live-trading` flag with explicit risk-limit
   parameters (max position, max daily loss, exchange whitelist).
3. Pass paper trading for **months** with realistic capital at stake.
4. Re-read REALITY-CHECK.md.

If any of those steps feels skippable, you are not ready. Stay in paper.

## Data feed only? Fine.

Using ccxt to *read* market data is harmless. The code only ever calls
`fetch_ohlcv`, never `create_order`. There is no `create_order` anywhere in
this repo. (Greppable check: `grep -rn create_order src/` → nothing.)
