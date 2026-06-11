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
                fee_bps=settings.taker_fee_bps,
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

            bench_strat = get_strategy("buy_and_hold")
            wf = WalkForward(
                engine=engine,
                folds=5,
                train_ratio=0.5,
                benchmark_strategy=bench_strat,
            )
            wfres = wf.run(df, strat)

            # Fold comparison vs benchmark
            comparison_rows: list[str] = []
            if wfres.benchmark_summary is not None:
                merged = wfres.summary.merge(
                    wfres.benchmark_summary, on="fold", suffixes=("_strat", "_bench")
                )
                if not merged.empty:
                    for _, row in merged.iterrows():
                        bench_ret = row.get("total_return_bench", 0)
                        strat_ret = row.get("total_return_strat", 0)
                        comparison_rows.append(
                            f"- fold {int(row['fold'])}: "
                            f"strategy={strat_ret * 100:.2f}% "
                            f"bench={bench_ret * 100:.2f}% "
                            f"Δ={(strat_ret - bench_ret) * 100:+.2f}%"
                        )

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

            if wfres.bootstrap_ci is not None:
                lo, hi = wfres.bootstrap_ci
                lines.append(f"- **sharpe 95% CI**: ({lo:.3f}, {hi:.3f})")
                lines.append(
                    f"- **CI includes zero?**: {'YES — no edge detected' if lo <= 0 <= hi else 'NO'}"
                )

            if comparison_rows:
                lines += ["", "## Strategy vs Benchmark", "", *comparison_rows]

            wf_path = wf_dir / f"{slug(symbol)}__{sname}.md"
            wf_path.write_text("\n".join(lines) + "\n")
            print(
                f"[walk-forward] {symbol} {sname}: "
                f"median_sharpe={wfres.aggregate.get('median_sharpe', 0):.3f} "
                f"win_folds={wfres.aggregate.get('win_folds', 0):.0f}/"
                f"{wfres.aggregate.get('total_folds', 0):.0f} "
                f"sharpe_ci={wfres.bootstrap_ci} "
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
