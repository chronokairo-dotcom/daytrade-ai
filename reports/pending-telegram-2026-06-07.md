# Pending Telegram delivery — 2026-06-07 11:00 UTC

Canal Telegram não configurado/disponível no gateway. Mensagem abaixo salva para entrega manual.

---

> Bom dia, ChronoKairo! Segue o relatório matinal do daytrade-ai (gerado 2026-05-01).

📊 Walk-forward: 0/6 runs com Sharpe positivo. Nenhum edge detectado.

📉 Full-range:
• BTC momentum: -96.97% (Sharpe -3.0)
• ETH momentum: -96.29% (Sharpe -2.1)
• ETH sma_cross: -0.5 Sharpe (melhor caso)

🔍 Pattern 1h — todos downtrend + chop:
• BTC $77.207, ADX 16, RSI 67 (+3.17σ)
• ETH $2.285, ADX 14, RSI 63 (+3.44σ)
• SOL $83.97, ADX 20, RSI 64 (+2.86σ)

🚨 P0 urgente:
1) Parar de construir estratégias até provar edge com benchmark
2) Auditar custos — 10bps fee + 5bps slippage é irreal
3) Significância estatística (bootstrap + permutação)

⚠️ P1:
• Walk-forward folds muito grossos — expanding window
• Pattern sem histórico — CLI de tendência
• Regime gating — estratégias rodam no chop sem filtrar

🟢 P2: testar 4h/1d, sanity test sintético

Veredito: todas perderam. Engine + custos precisam de auditoria antes de qualquer nova estratégia. :>
