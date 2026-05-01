#!/usr/bin/env python
"""daytrade-ai pattern analysis service.

Periodically refreshes OHLCV data and writes a structured pattern report.
Paper-only: only public OHLCV endpoints, never balance / order endpoints.

Loop policy:
  - Default interval: 30 minutes
  - Per-symbol exception isolation (one bad symbol does not kill the loop)
  - Logs every iteration to logs/pattern_service.log (size-rotation based on
    a single file with monotonic append; rotate manually with logrotate or
    systemd-tmpfiles if needed)

Outputs:
  - reports/patterns/<symbol>__<timeframe>__<utcdate>.md (one per pass)
  - reports/patterns/latest.md (aggregated snapshot)
  - reports/patterns/history.jsonl (one row per (timestamp, symbol))
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from daytrade_ai.analysis.patterns import analyze_patterns, render_markdown  # noqa: E402
from daytrade_ai.config import get_settings  # noqa: E402
from daytrade_ai.data.ccxt_source import CCXTDataSource  # noqa: E402

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_TIMEFRAME = "1h"
DEFAULT_EXCHANGE = "binance"
DEFAULT_LOOKBACK = 720

LOG_DIR = ROOT / "logs"
REPORT_DIR = ROOT / "reports" / "patterns"


def _ts() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def _log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{_ts()} {msg}\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    with (LOG_DIR / "pattern_service.log").open("a") as f:
        f.write(line)


def run_once(
    symbols: list[str],
    timeframe: str,
    exchange: str,
    lookback: int,
) -> int:
    """Run a single pass. Returns number of successful symbols."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    src = CCXTDataSource(exchange=exchange, cache_dir=settings.cache_dir)

    aggregated: list[str] = [
        "# Pattern report :: latest snapshot",
        "",
        f"_generated: {_ts()}_",
        "",
    ]
    history_path = REPORT_DIR / "history.jsonl"
    successes = 0

    for symbol in symbols:
        try:
            _log(f"refresh symbol={symbol} tf={timeframe}")
            df = src.fetch(symbol=symbol, timeframe=timeframe)
            if df.empty:
                _log(f"empty data symbol={symbol}")
                aggregated.append(f"## {symbol}\n\n_no data_\n")
                continue
            if lookback > 0:
                df = df.tail(lookback)
            rep = analyze_patterns(df, symbol=symbol, timeframe=timeframe)
            md = render_markdown(rep, generated_at=datetime.now(tz=UTC))

            # Per-symbol dated file
            safe = symbol.replace("/", "-")
            utcdate = datetime.now(tz=UTC).strftime("%Y%m%d")
            (REPORT_DIR / f"{safe}__{timeframe}__{utcdate}.md").write_text(md)

            # Append to history
            with history_path.open("a") as f:
                f.write(
                    json.dumps(
                        {"ts": _ts(), "symbol": symbol, "timeframe": timeframe, **asdict(rep)},
                        default=str,
                    )
                    + "\n"
                )

            aggregated.append(md)
            aggregated.append("")
            successes += 1
            _log(
                f"ok symbol={symbol} trend={rep.trend_regime} adx={rep.adx_value:.2f} "
                f"rsi={rep.rsi_14:.2f} z={rep.zscore_close_sma20:+.2f}"
            )
        except Exception as e:
            _log(f"error symbol={symbol} err={e!r}")
            _log("traceback: " + traceback.format_exc().replace("\n", " | "))
            aggregated.append(f"## {symbol}\n\n_error: {e!r}_\n")

    (REPORT_DIR / "latest.md").write_text("\n".join(aggregated) + "\n")
    _log(f"pass complete symbols_ok={successes}/{len(symbols)}")
    return successes


def main() -> int:
    parser = argparse.ArgumentParser(description="daytrade-ai pattern analysis service")
    parser.add_argument(
        "--symbol", action="append", default=None, help="May be passed multiple times."
    )
    parser.add_argument("--timeframe", default=DEFAULT_TIMEFRAME)
    parser.add_argument("--exchange", default=DEFAULT_EXCHANGE)
    parser.add_argument("--lookback-bars", type=int, default=DEFAULT_LOOKBACK)
    parser.add_argument("--interval-min", type=int, default=30)
    parser.add_argument("--once", action="store_true", help="Run one pass and exit.")
    args = parser.parse_args()

    symbols = args.symbol or DEFAULT_SYMBOLS
    _log(
        f"starting pattern_service symbols={symbols} tf={args.timeframe} "
        f"exchange={args.exchange} interval_min={args.interval_min} once={args.once}"
    )

    iteration = 0
    while True:
        iteration += 1
        t0 = time.time()
        try:
            run_once(symbols, args.timeframe, args.exchange, args.lookback_bars)
        except Exception as e:
            _log(f"FATAL pass error: {e!r}")
            _log("traceback: " + traceback.format_exc().replace("\n", " | "))
        dt = time.time() - t0
        _log(f"iteration={iteration} elapsed={dt:.1f}s")

        if args.once:
            break

        sleep_s = max(60, args.interval_min * 60)
        _log(f"sleeping {sleep_s}s")
        time.sleep(sleep_s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
