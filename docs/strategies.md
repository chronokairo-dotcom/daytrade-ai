# Strategies

All strategies subclass `daytrade_ai.strategies.base.Strategy` and self-register
via the `@register("name")` decorator. Adding a new file under
`src/daytrade_ai/strategies/` and importing it from
`src/daytrade_ai/strategies/__init__.py` is enough to make it discoverable.

## sma_cross

Simple moving-average crossover.

- params: `fast` (default 10), `slow` (default 30), `allow_short` (default False)
- signal: `+1` when `SMA(fast) > SMA(slow)`, `0` (or `-1` if `allow_short`)
  otherwise.
- caveats: classic curve-fits like crazy on in-sample data. Walk-forward
  before believing anything.

## rsi_mean_reversion

Long when RSI < `oversold` (default 30), exit when RSI > `exit_above`
(default 55). Stateful sweep over RSI values.

- caveats: works in mean-reverting regimes, devastates the equity curve in
  trending markets. Pair with a regime filter before serious use.

## momentum

Long when the rolling `lookback`-bar return exceeds `threshold` (default 0).

- caveats: lookback choice is everything. Underperforms in chop. Strongly
  recommend pairing with volatility filters.

## A word from REALITY-CHECK

These are *educational* baselines. None of them is a money printer. The point
of this repo is to make it easy to test honest hypotheses with honest costs.
