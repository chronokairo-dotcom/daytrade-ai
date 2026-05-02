#!/usr/bin/env python
"""Run backtest + walk-forward for {BTC,ETH}/USDT × {sma_cross, rsi_mean_reversion, momentum}.

Uses cached data only (no network); falls back gracefully if cache is missing.
Writes reports under reports/backtests/ and reports/walk-forward/.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from daytrade_ai.backtest.engine import BacktestEngine  # noqa: E402
from daytrade_ai.backtest.walk_forward import WalkForward  # noqa: E402
from daytrade_ai.config import get_settings  # noqa: E402
from daytrade_ai.data.cache import cache_path, read_cache  # noqa: E402
from daytrade_ai.reporting.report import format_markdown_report  # noqa: E402
from daytrade_ai.strategies import get_strategy  # noqa: E402

SYMBOLS = ["BTC/USDT", "ETH/USDT"]
STRATS = ["sma_cross", "rsi_mean_reversion", "momentum"]
TIMEFRAME = "1h"
EXCHANGE = "binance"


def slug(s: str) -> str:
    return s.replace("/", "-")


def main() -> int:
    settings = get_settings()
    bt_dir = ROOT / "reports" / "backtests"
    wf_dir = ROOT / "reports" / "walk-forward"
    bt_dir.mkdir(parents=True, exist_ok=True)
    wf_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, object]] = []

    for symbol in SYMBOLS:
        df = read_cache(cache_path(settings.cache_dir, EXCHANGE, symbol, TIMEFRAME))
        if df is None or df.empty:
            print(f"[skip] no cache for {symbol}")
            continue
        print(f"[data] {symbol}: {len(df)} bars {df.index[0]} → {df.index[-1]}")

        for sname in STRATS:
            strat = get_strategy(sname)
            engine = BacktestEngine(
                initial_cash=settings.initial_cash,
                fee_bps=settings.fee_bps,
                slippage_bps=settings.slippage_bps,
            )
            res = engine.run(df, strat)
            title = f"{sname} :: {symbol} :: {TIMEFRAME}"
            md = format_markdown_report(res, title=title)
            path = bt_dir / f"{slug(symbol)}__{sname}__{TIMEFRAME}.md"
            path.write_text(md)
            print(
                f"[backtest] {symbol} {sname}: ret={res.metrics.get('total_return', 0):.4f} "
                f"sharpe={res.metrics.get('sharpe', 0):.3f} "
                f"trades={int(res.metrics.get('n_trades', 0))} "
                f"-> {path.relative_to(ROOT)}"
            )
            summary.append(
                {
                    "kind": "backtest",
                    "symbol": symbol,
                    "strategy": sname,
                    "metrics": res.metrics,
                }
            )

            wf = WalkForward(engine=engine, folds=5, train_ratio=0.5)
            wfres = wf.run(df, strat)
            lines = [
                f"# Walk-forward :: {sname} :: {symbol} :: {TIMEFRAME}",
                "",
                "- folds: 5, train_ratio: 0.5",
                f"- bars: {len(df)}",
                f"- range: {df.index[0]} → {df.index[-1]}",
                "",
                "## Per-fold",
                "",
                "```",
                wfres.summary.to_string(index=False),
                "```",
                "",
                "## Aggregate",
                "",
            ]
            for k, v in wfres.aggregate.items():
                lines.append(f"- **{k}**: {v:.4f}")
            wf_path = wf_dir / f"{slug(symbol)}__{sname}.md"
            wf_path.write_text("\n".join(lines) + "\n")
            print(
                f"[walk-forward] {symbol} {sname}: "
                f"median_sharpe={wfres.aggregate.get('median_sharpe', 0):.3f} "
                f"win_folds={wfres.aggregate.get('win_folds', 0):.0f}/"
                f"{wfres.aggregate.get('total_folds', 0):.0f} "
                f"-> {wf_path.relative_to(ROOT)}"
            )
            summary.append(
                {
                    "kind": "walk_forward",
                    "symbol": symbol,
                    "strategy": sname,
                    "aggregate": wfres.aggregate,
                }
            )

    out = ROOT / "reports" / "summary.json"
    out.write_text(
        json.dumps({"generated_at": datetime.now(tz=UTC).isoformat(), "results": summary}, indent=2)
    )
    print(f"\nWrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
