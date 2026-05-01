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

_Criado por Laciels (chronokairo machine) — `:>`_
