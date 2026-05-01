# Pattern Service Ops Cheatsheet

`scripts/pattern_service.py` is a long-running, paper-only background loop that
refreshes OHLCV data from Binance public endpoints and writes structured
pattern reports.

## What it does

Every `--interval-min` minutes (default 30) it:

1. Fetches the latest OHLCV via ccxt public endpoints (no API key, no auth).
2. Tail-trims to `--lookback-bars` (default 720 bars = 30 days @ 1h).
3. Computes a `PatternReport` (trend / volatility / momentum / mean reversion /
   range stats / candle pattern counts).
4. Writes:
   - `reports/patterns/<symbol>__<timeframe>__<utcdate>.md` per symbol per pass
   - `reports/patterns/latest.md` aggregated snapshot
   - `reports/patterns/history.jsonl` row per (timestamp, symbol)
   - `logs/pattern_service.log` line-buffered append log

Per-symbol exceptions are caught — one bad fetch never kills the loop.

## Hard guarantees

- **PAPER ONLY.** No order calls, no balance calls, no auth. Only public OHLCV.
- No API keys consumed. Public ccxt endpoints work without credentials.

## Run it manually

```bash
. .venv/bin/activate
python scripts/pattern_service.py --once                          # one pass
python scripts/pattern_service.py --interval-min 30               # loop
python scripts/pattern_service.py --symbol BTC/USDT --once        # single
python scripts/pattern_service.py --symbol BTC/USDT --symbol ETH/USDT --interval-min 15
```

## systemd

Unit: `/etc/systemd/system/daytrade-ai-pattern.service`

```bash
systemctl daemon-reload
systemctl enable --now daytrade-ai-pattern.service
systemctl status daytrade-ai-pattern.service
journalctl -u daytrade-ai-pattern.service -f --no-pager
```

Stop / restart:

```bash
systemctl stop daytrade-ai-pattern.service
systemctl restart daytrade-ai-pattern.service
systemctl disable daytrade-ai-pattern.service
```

## Files at a glance

| Path | What |
|---|---|
| `reports/patterns/latest.md` | Latest aggregated snapshot (overwritten each pass) |
| `reports/patterns/history.jsonl` | Append-only structured history (one row per symbol per pass) |
| `reports/patterns/<symbol>__<timeframe>__<utcdate>.md` | Per-symbol per-day report |
| `logs/pattern_service.log` | Service log (also goes to journald via systemd) |

## Log rotation

The service appends to `logs/pattern_service.log` indefinitely. For a long-lived
deployment add a logrotate config such as:

```
/root/.openclaw/workspace/daytrade-ai/logs/pattern_service.log {
    weekly
    rotate 4
    missingok
    notifempty
    compress
    copytruncate
}
```

Or rely on `journalctl` (the unit also writes to journal).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `error symbol=… err=NetworkError` | Binance public API hiccup | Service auto-retries next interval. |
| Empty `latest.md` | Cache and network both dead | Check `journalctl -u daytrade-ai-pattern -n 100`. |
| Service flapping (Restart loop) | Python import error | `systemctl status` + journal will show stack trace. |
