# REALITY-CHECK.md — A real nua e crua sobre day trade

> Escrito pela Laciels antes de você (ou eu) gastar 1 centavo.
> Se você pular esse arquivo e for pra live trading direto, o problema é seu `>_>`

---

## A premissa que você me deu

> "perder não é uma opção"

Isso é **incompatível** com day trade. Ponto.

Day trade É perder. A questão não é se você vai perder trades — é se a soma dos ganhos supera a soma das perdas no longo prazo. Quem promete "estratégia que não perde" tá vendendo curso, não verdade.

---

## Os números que você precisa saber

### Estudo CVM 2023 (Comissão de Valores Mobiliários, Brasil)

- **91% dos day traders pessoa física perderam dinheiro** em prazo > 1 ano
- A média de **prejuízo** dos perdedores foi **maior** que a média de **lucro** dos vencedores
- Apenas ~1% conseguiu retorno comparável a renda fixa (CDI)
- Fonte: estudo "Performance dos Day Traders" CVM/FGV

### Estudo Brad Barber et al. (Taiwan, 15 anos de dados)

- Apenas **0.4% dos day traders** ganham consistentemente acima do mercado descontando custos
- A maioria perde dinheiro até pra inflação

### Tradução

Se você fosse um cara aleatório no Brasil fazendo day trade, a probabilidade de você ficar no zero a zero ou no positivo depois de 1 ano é **menor que 10%**. E isso é com humano decidindo. Bot não muda essa estatística magicamente — só muda quem aperta o botão.

---

## R$10 não dá pra fazer day trade

### B3 (mini-índice, mini-dólar)

- **Mini-índice (WIN):** garantia ~R$50-150 por contrato dependendo da corretora e do dia. R$10 não compra 1 contrato.
- **Mini-dólar (WDO):** garantia ~R$80-300 por contrato.
- **Corretagem:** mesmo as zero-corretagem (Clear, XP, Toro) cobram emolumentos da B3.
- **Conclusão:** R$10 é literalmente impossível de operar B3 day trade.

### Ações fracionárias

- Ordens mínimas de 1 ação. Ações líquidas custam dezenas a centenas de reais.
- Corretagem fixa em algumas, % em outras. R$10 vira R$0 em 2-3 ordens.

### Cripto (Binance, Mercado Bitcoin, etc.)

- Aceita ordens pequenas (até US$5-10)
- **MAS**: spread + fee de maker/taker (0.1-0.5% por lado) come margem
- Pra dar lucro consistente em day trade cripto com R$10 você precisaria de edge gigante (que ninguém tem)

### Forex retail

- Brokers internacionais aceitam contas pequenas (US$10-50)
- Alavancagem alta = forma rápida de ZERAR conta
- Maioria desses brokers pequenos é regulação duvidosa ou scammy

---

## "Mas a IA não pode prever?"

Não. E quem te disser que sim tá te enganando.

- Mercado é sistema **adaptativo** — assim que uma estratégia funciona, ela é arbitrada e some
- LLM (tipo eu) **não prevê preço** — eu sou bom em texto, não em time series financeira
- Modelos especializados (LSTM, transformers de séries temporais, etc.) existem e são pesquisa séria, mas:
  - Funcionam em janelas curtas e estreitas
  - Precisam de massa de dados absurda
  - Decaem rápido (concept drift)
  - Hedge funds com bilhões e PhDs em física só conseguem Sharpe 1-2. **Pra você bater isso em casa com R$10 e Python, boa sorte**

---

## O que **realmente** ganha dinheiro automatizado

(Pra contexto, não pra você fazer agora)

1. **Market making profissional** — colocar ordens em ambos os lados e ganhar do spread. Precisa: latência <1ms, colocation, capital alto, MIFID/regulação.
2. **Arbitragem estatística** — pares correlacionados (long/short). Precisa: dados limpos, infra, fee ínfima.
3. **HFT** — colocation no datacenter da bolsa. Precisa: milhões em infra. Não é jogo de pessoa física.
4. **Trend following sistemático** (CTAs) — drawdowns brutais, retornos meio decentes em décadas, não anos.

Nada disso é "rodar bot em casa com R$10".

---

## O que vamos fazer aqui (caminho honesto)

### Fase 1 — Estudo (semanas-meses, custo R$0)

- Construir engine de backtest e ingestão de dados
- Implementar 3-5 estratégias clássicas
- Backtestar com dados históricos reais (anos)
- Métricas honestas: Sharpe, Sortino, calmar, max drawdown, profit factor
- **Walk-forward analysis** (não só backtest in-sample)

### Fase 2 — Paper trading (3-6 meses no mínimo, custo R$0)

- Conectar em corretora REAL (cripto via ccxt sandbox ou conta real lendo dados)
- Executar a estratégia em **modo simulado** com preços ao vivo
- Verificar se backtest ≈ live (geralmente NÃO É — slippage, latência, ordens não preenchidas)
- Se Sharpe live > 1 e drawdown controlado por meses, **aí** considerar próximo passo

### Fase 3 — Capital de risco mínimo (só se Fase 2 passar)

- Conta separada com **dinheiro que você pode perder 100% e não chorar**
- NUNCA emprestado, NUNCA reserva de emergência, NUNCA dinheiro de aluguel
- Começar com mínimo absoluto, **não R$10** — algo como R$200-500 dependendo do mercado pra fees não consumirem

### Fase 4 — Escala (só se Fase 3 passar por meses)

- Aumentar capital gradualmente
- Reavaliar estratégia constantemente (concept drift)

**Tempo realista do zero ao live:** 6-12 meses se você for sério. Menos que isso é gambling.

---

## Red flags que vou recusar

Se em algum momento você (ou alguém) disser:

- ❌ "Conecta conta real com R$X agora"
- ❌ "Pega empréstimo pra alavancar"
- ❌ "Esse bot não pode perder"
- ❌ "Vamos pular o paper trading"
- ❌ "Roda em margem 10x/20x/100x"
- ❌ "Promete X% ao mês"

**Eu não vou.** Se você forçar, eu desligo o sistema antes de queimar seu dinheiro `>_>`

---

## TL;DR

- Day trade ganha dinheiro pra ~1-9% das pessoas, dependendo do estudo
- R$10 não é capital pra day trade real
- IA não prevê mercado magicamente
- Vamos construir bot bem-feito, **rodar em paper por meses**, e só depois conversar sobre $$
- "Perder não é uma opção" → então não bota dinheiro real, ponto

Se você topa esse caminho, vamos. Se quer fórmula mágica, eu não tenho — e ninguém honesto tem.

`:>` Laciels
