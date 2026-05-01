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
    lines.append(
        f"- {len(wf_rows)} (symbol × strategy) walk-forward runs completed."
    )
    lines.append(
        f"- **{n_pos}** had positive median Sharpe; **{n_neg}** had negative or zero."
    )
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
    # Urgent changes (the brutally honest part)
    # ------------------------------------------------------------------
    items: list[tuple[str, str, str, str, str]] = [
        # (priority, title, why, change, effort)
        (
            "🔴 P0",
            "Stop building strategies until edge is demonstrated on a benchmark",
            (
                "All three bundled strategies have negative median Sharpe on both BTC/USDT "
                "and ETH/USDT walk-forward (1h, 2023→2026). Adding more strategies without "
                "first proving the engine + cost model can find any positive baseline is "
                "research theatre."
            ),
            (
                "Add a buy-and-hold benchmark in `src/daytrade_ai/strategies/buy_and_hold.py` "
                "and a relative-performance column in walk-forward summaries "
                "(`backtest/walk_forward.py`)."
            ),
            "S (1–2h)",
        ),
        (
            "🔴 P0",
            "Realistic cost model audit: 10 bps fee + 5 bps slippage on 1h is borderline insane",
            (
                "Momentum strategy fires 1500+ trades over the test window and dies — most "
                "of the loss is friction. The defaults assume retail Binance maker fees, "
                "but every fill is treated as a taker with directional slippage. This biases "
                "all conclusions."
            ),
            (
                "In `backtest/engine.py` separate maker/taker fee, model partial fills "
                "(or at least cap turnover per bar). Add a `--zero-cost` sanity-check flag "
                "to the CLI to confirm strategies *would* be profitable before friction."
            ),
            "M (3–5h)",
        ),
        (
            "🔴 P0",
            "No statistical significance gates",
            (
                "We report Sharpe to 3 decimal places without any confidence interval. "
                "On 5 folds that's noise. There is no way to distinguish 'bad strategy' "
                "from 'unlucky strategy' as currently reported."
            ),
            (
                "Add bootstrap confidence intervals to `metrics/performance.py` and a "
                "permutation test that shuffles signals to estimate the null distribution. "
                "Refuse to declare 'edge' unless median Sharpe > 95th percentile of null."
            ),
            "M (4–6h)",
        ),
        (
            "🟡 P1",
            "Walk-forward folds are too coarse and overlap nothing",
            (
                "Current implementation uses 5 contiguous folds with a 50/50 train/test "
                "split *within each fold*. That's not really walk-forward — it's 5 "
                "independent in-sample/out-of-sample splits with no anchor."
            ),
            (
                "Refactor `backtest/walk_forward.py` to support anchored expanding-window "
                "or rolling-window walk-forward with a configurable step size."
            ),
            "M (3–4h)",
        ),
        (
            "🟡 P1",
            "Pattern report has no historical comparison",
            (
                "`reports/patterns/latest.md` is a snapshot. We persist `history.jsonl` but "
                "nothing reads it. Regime changes are invisible."
            ),
            (
                "Add a `pattern-trend` CLI that plots ATR percentile, RSI, and ADX over the "
                "last N passes from `history.jsonl`. Markdown sparkline / ascii is fine."
            ),
            "S (2h)",
        ),
        (
            "🟡 P1",
            "No regime gating on strategies",
            (
                "Latest pattern snapshot shows ADX in the 13–20 range across BTC/ETH/SOL "
                "(chop). SMA cross and momentum should be disabled in chop; RSI mean-revert "
                "should only fire then. The strategies don't read the regime at all."
            ),
            (
                "Add an optional `regime_filter` mixin that consults a `PatternReport` and "
                "zeros signals outside the appropriate regime bucket."
            ),
            "M (3h)",
        ),
        (
            "🟢 P2",
            "Multi-timeframe alignment",
            (
                "1h is too noisy for trend-following with these defaults. Should at least "
                "test 4h and 1d before declaring strategies dead."
            ),
            (
                "Run `scripts/run_realdata_analysis.py` parameterized over a list of "
                "timeframes; cache and emit a heatmap markdown table."
            ),
            "S (1h)",
        ),
        (
            "🟢 P2",
            "Add a synthetic-data sanity test",
            (
                "We have no end-to-end test that proves the engine recovers a known edge "
                "from a deterministic series (e.g. perfect oracle signal → near-100% return)."
            ),
            (
                "Add `tests/test_engine_sanity.py` that constructs a sine wave + an oracle "
                "strategy and asserts the engine yields >> 0 Sharpe."
            ),
            "S (1h)",
        ),
    ]

    lines.append("## Urgent changes")
    lines.append("")
    for prio, title, why, change, effort in items:
        lines.append(f"### {prio} — {title}")
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
