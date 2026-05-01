# daytrade-ai

> Bot de day trade automatizado — em desenvolvimento, **paper trading only**.

⚠️ **LEIA O [REALITY-CHECK.md](./REALITY-CHECK.md) ANTES DE QUALQUER COISA.**

## Status

🚧 Repositório recém-criado. Sem código ainda. Sem dinheiro real conectado. Não vai conectar tão cedo.

## Filosofia

- **Paper trading primeiro, sempre.** Nada de capital real até a estratégia provar Sharpe > 1 com drawdown controlado por meses.
- **Backtest honesto.** Slippage, fees, latência. Sem fitting de curva.
- **Pequenos passos.** Indicador → estratégia → backtest → walk-forward → paper → (talvez um dia) live.
- **Transparência.** Tudo logado. Toda decisão auditável.

## Roadmap inicial

- [ ] Ingestão de dados (cripto via ccxt, ações/futuros B3 via yfinance/MetaTrader)
- [ ] Engine de backtest (provavelmente vectorbt ou backtrader)
- [ ] Estratégias-base de estudo: SMA crossover, RSI mean reversion, momentum
- [ ] Métricas: Sharpe, Sortino, max drawdown, win rate, profit factor
- [ ] Walk-forward analysis
- [ ] Paper trading conectado a corretora real (sem $$ exposto)
- [ ] Dashboard de monitoramento

## License

MIT (ou o que decidirmos)

---

## Usage

> **Paper trading only.** This project does not place real orders. See
> [REALITY-CHECK.md](./REALITY-CHECK.md) and [docs/paper-trading.md](./docs/paper-trading.md).

### Install (dev)

```bash
make install        # creates .venv and `pip install -e ".[dev]"`
source .venv/bin/activate
```

Or manually:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Run the demo backtest

```bash
make backtest-demo
# or:
python -m daytrade_ai.cli backtest --strategy sma_cross --csv tests/fixtures/btc_sample.csv
```

### CLI commands

```bash
daytrade-ai list-strategies
daytrade-ai fetch-data    --symbol BTC/USDT --timeframe 1h --since 2023-01-01
daytrade-ai backtest      --strategy sma_cross --symbol BTC/USDT --timeframe 1h --since 2023-01-01
daytrade-ai walk-forward  --strategy sma_cross --folds 5 --csv tests/fixtures/btc_sample.csv
daytrade-ai paper         --strategy sma_cross --symbol BTC/USDT --timeframe 1h --iterations 1
```

### Quality gates

```bash
make lint        # ruff check + format check
make typecheck   # mypy --strict
make test        # pytest
```

### Project layout

```
src/daytrade_ai/    package source (data, strategies, backtest, metrics, paper, reporting)
tests/              pytest suite + tiny CSV fixture
docs/               architecture + strategies + paper-trading docs
notebooks/          exploration template
```

See [docs/architecture.md](./docs/architecture.md) for the data-flow diagram.

---

_Criado por Laciels (chronokairo machine) — `:>`_
