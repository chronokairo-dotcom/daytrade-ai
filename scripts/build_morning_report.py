#!/usr/bin/env python
"""Build the morning report.

Aggregates:
  1. Walk-forward results from reports/walk-forward/*.md (and reports/summary.json)
  2. Latest pattern report from reports/patterns/latest.md
  3. Prioritized list of urgent changes (P0/P1/P2)
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(p: Path) -> str:
    return p.read_text() if p.exists() else ""


def main() -> int:
    summary_path = ROOT / "reports" / "summary.json"
    latest_patterns = ROOT / "reports" / "patterns" / "latest.md"
    out = ROOT / "reports" / "morning-report.md"

    wf_rows: list[dict] = []
    bt_rows: list[dict] = []
    if summary_path.exists():
        data = json.loads(summary_path.read_text())
        for r in data.get("results", []):
            if r["kind"] == "walk_forward":
                wf_rows.append(r)
            elif r["kind"] == "backtest":
                bt_rows.append(r)

    lines: list[str] = []
    ts = datetime.now(tz=UTC).isoformat(timespec="seconds")
    lines.append("# daytrade-ai :: morning report")
    lines.append("")
    lines.append(f"_generated: {ts}_")
    lines.append("")
    lines.append("> **PAPER ONLY.** This report describes research-grade backtests on cached")
    lines.append("> Binance public OHLCV data. No live orders. No claims of profitability.")
    lines.append("")

    # ------------------------------------------------------------------
    # TL;DR
    # ------------------------------------------------------------------
    n_neg = sum(1 for r in wf_rows if r["aggregate"].get("median_sharpe", 0) < 0)
    n_pos = sum(1 for r in wf_rows if r["aggregate"].get("median_sharpe", 0) > 0)
    lines.append("## TL;DR")
    lines.append("")
    lines.append(f"- {len(wf_rows)} (symbol × strategy) walk-forward runs completed.")
    lines.append(f"- **{n_pos}** had positive median Sharpe; **{n_neg}** had negative or zero.")
    if n_pos == 0:
        lines.append(
            "- **Verdict: no edge detected.** Every bundled strategy lost money on out-of-sample folds for both BTC/USDT and ETH/USDT."
        )
    lines.append(
        "- Recommendation: stop adding strategies until the engine, costs, and validation are audited. See P0 items below."
    )
    lines.append("")

    # ------------------------------------------------------------------
    # Walk-forward table
    # ------------------------------------------------------------------
    lines.append("## Walk-forward results (5 folds, train_ratio=0.5)")
    lines.append("")
    lines.append("| Symbol | Strategy | median Sharpe | mean ret | mean MaxDD | win folds |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for r in sorted(wf_rows, key=lambda x: (x["symbol"], x["strategy"])):
        a = r["aggregate"]
        lines.append(
            f"| {r['symbol']} | {r['strategy']} | "
            f"{a.get('median_sharpe', 0):.3f} | "
            f"{a.get('mean_total_return', 0) * 100:.2f}% | "
            f"{a.get('mean_max_drawdown', 0) * 100:.2f}% | "
            f"{int(a.get('win_folds', 0))}/{int(a.get('total_folds', 0))} |"
        )
    lines.append("")

    # ------------------------------------------------------------------
    # Full-range backtest summary
    # ------------------------------------------------------------------
    lines.append("## Full-range backtest (2023-01-01 → now)")
    lines.append("")
    lines.append("| Symbol | Strategy | total return | Sharpe | MaxDD | trades |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for r in sorted(bt_rows, key=lambda x: (x["symbol"], x["strategy"])):
        m = r["metrics"]
        lines.append(
            f"| {r['symbol']} | {r['strategy']} | "
            f"{m.get('total_return', 0) * 100:.2f}% | "
            f"{m.get('sharpe', 0):.3f} | "
            f"{m.get('max_drawdown', 0) * 100:.2f}% | "
            f"{int(m.get('n_trades', 0))} |"
        )
    lines.append("")

    # ------------------------------------------------------------------
    # Latest patterns snapshot
    # ------------------------------------------------------------------
    lines.append("## Latest pattern snapshot")
    lines.append("")
    pat = _read(latest_patterns).strip()
    if pat:
        # Indent under H2 by demoting H1s.
        for raw in pat.splitlines():
            if raw.startswith("# "):
                lines.append("### " + raw[2:])
            elif raw.startswith("## "):
                lines.append("#### " + raw[3:])
            else:
                lines.append(raw)
    else:
        lines.append("_no pattern report available_")
    lines.append("")

    # ------------------------------------------------------------------
    # Urgent changes — detect what's already implemented vs still needed
    # ------------------------------------------------------------------
    def _check_implemented(src_rel: str, hints: list[str]) -> bool:
        p = ROOT / "src" / src_rel
        if not p.exists():
            return False
        text = p.read_text()
        return all(h in text for h in hints)

    items: list[tuple[str, str, str, str, str, bool]] = [
        (
            "🔴 P0",
            "Stop building strategies until edge is demonstrated on a benchmark",
            "All three bundled strategies still have negative median Sharpe across BTC/ETH.",
            "Buy-and-hold benchmark + walk-forward comparison is implemented. Verify it's wired into run_realdata_analysis.py.",
            "S (check & wire)",
            _check_implemented("daytrade_ai/strategies/buy_and_hold.py", ["BuyAndHold"]),
        ),
        (
            "🔴 P0",
            "Realistic cost model audit",
            "Momentum fires 1500+ trades and most loss is friction.",
            "Zero-cost mode, maker/taker fee split, and min-bars-between-trades cap implemented in engine. Use --zero-cost to sanity-check before friction.",
            "M (audit usage)",
            _check_implemented(
                "daytrade_ai/backtest/engine.py",
                ["zero_cost_mode", "maker_fee_bps", "use_taker_fee"],
            ),
        ),
        (
            "🔴 P0",
            "No statistical significance gates",
            "Sharpe without CI is noise on 5 folds.",
            "Bootstrap 95% CI + permutation test implemented in metrics/performance.py. Walk-forward now reports bootstrap_ci in both fixed and rolling modes.",
            "M (wire into analysis)",
            _check_implemented(
                "daytrade_ai/metrics/performance.py",
                ["bootstrap_sharpe_ci", "permutation_sharpe_test"],
            ),
        ),
        (
            "🟡 P1",
            "Walk-forward folds are too coarse",
            "5 contiguous folds with no anchor.",
            "Expanding/rolling window modes implemented in walk_forward.py with configurable step_size.",
            "M (test coverage)",
            _check_implemented(
                "daytrade_ai/backtest/walk_forward.py", ["WindowMode", "EXPANDING", "ROLLING"]
            ),
        ),
        (
            "🟡 P1",
            "Pattern report has no historical comparison",
            "history.jsonl exists but nothing reads it.",
            "pattern-trend CLI command implemented with sparkline visualization.",
            "S (docs)",
            _check_implemented("daytrade_ai/cli.py", ["pattern_trend_cmd"]),
        ),
        (
            "🟡 P1",
            "No regime gating on strategies",
            "ADX chop means trend strategies bleed.",
            "RegimeFilterMixin implemented in base.py. Strategies can opt in by setting regime_allowlist.",
            "M (enable per-strategy)",
            _check_implemented("daytrade_ai/strategies/base.py", ["RegimeFilterMixin"]),
        ),
        (
            "🟢 P2",
            "Multi-timeframe alignment",
            "1h is too noisy; need 4h and 1d tests too.",
            "Implement heatmap driver that iterates timeframes in run_realdata_analysis.py.",
            "S (1h)",
            False,
        ),
        (
            "🟢 P2",
            "Add a synthetic-data sanity test",
            "No e2e test proving engine recovers known edge.",
            "tests/test_engine_sanity.py exists with oracle strategy + zero-cost mode tests.",
            "S (done)",
            _check_implemented("tests/test_engine_sanity.py", ["test_engine_recovers_known_edge"]),
        ),
    ]

    lines.append("## Urgent changes")
    lines.append("")
    for prio, title, why, change, effort, done in items:
        status = "✅ Fixed" if done else "❌ Open"
        lines.append(f"### {prio} — {title} [{status}]")
        lines.append("")
        lines.append(f"**Why.** {why}")
        lines.append("")
        lines.append(f"**Change.** {change}")
        lines.append("")
        lines.append(f"**Effort.** {effort}")
        lines.append("")

    out.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
