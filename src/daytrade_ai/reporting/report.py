"""Text + markdown reports for backtest results."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from daytrade_ai.backtest.engine import BacktestResult


def ascii_equity_curve(equity: pd.Series, width: int = 60, height: int = 12) -> str:
    if equity.empty:
        return "(empty equity curve)"
    values = equity.to_numpy(dtype=float)
    if len(values) > width:
        # Bucket-average down to `width` columns.
        step = len(values) / width
        sampled = [
            float(values[int(i * step) : max(int((i + 1) * step), int(i * step) + 1)].mean())
            for i in range(width)
        ]
    else:
        sampled = list(values)

    lo = min(sampled)
    hi = max(sampled)
    span = hi - lo or 1.0
    rows: list[list[str]] = [[" "] * len(sampled) for _ in range(height)]
    for x, v in enumerate(sampled):
        y = int((v - lo) / span * (height - 1))
        y = (height - 1) - y
        rows[y][x] = "*"
    border = "+" + "-" * len(sampled) + "+"
    body = "\n".join("|" + "".join(r) + "|" for r in rows)
    return f"{border}\n{body}\n{border}\nmin={lo:.2f}  max={hi:.2f}"


def format_text_report(result: BacktestResult, title: str = "Backtest") -> str:
    m = result.metrics
    lines = [
        f"=== {title} ===",
        f"bars            : {int(m.get('n_bars', 0))}",
        f"trades          : {int(m.get('n_trades', 0))}",
        f"initial cash    : {result.initial_cash:.2f}",
        f"final equity    : {float(result.equity_curve.iloc[-1]) if len(result.equity_curve) else 0.0:.2f}",
        f"total return    : {m['total_return'] * 100:.2f}%",
        f"CAGR            : {m['cagr'] * 100:.2f}%",
        f"sharpe          : {m['sharpe']:.3f}",
        f"sortino         : {m['sortino']:.3f}",
        f"calmar          : {m['calmar']:.3f}",
        f"max drawdown    : {m['max_drawdown'] * 100:.2f}%",
        f"win rate        : {m['win_rate'] * 100:.2f}%",
        f"profit factor   : {m['profit_factor']:.3f}",
        f"expectancy ($)  : {m['expectancy']:.4f}",
        f"fees / slippage : {result.fee_bps:.1f} bps / {result.slippage_bps:.1f} bps per side",
        "",
        "Equity curve:",
        ascii_equity_curve(result.equity_curve),
        "",
        "NOTE: backtest results assume historical fills at modeled prices.",
        "      Real markets have additional latency, partial fills, and concept drift.",
        "      Paper-trade for months before considering anything beyond research.",
    ]
    return "\n".join(lines)


def format_markdown_report(result: BacktestResult, title: str = "Backtest") -> str:
    m = result.metrics
    rows = [
        ("Bars", f"{int(m.get('n_bars', 0))}"),
        ("Trades", f"{int(m.get('n_trades', 0))}"),
        ("Initial cash", f"{result.initial_cash:.2f}"),
        (
            "Final equity",
            f"{float(result.equity_curve.iloc[-1]) if len(result.equity_curve) else 0.0:.2f}",
        ),
        ("Total return", f"{m['total_return'] * 100:.2f}%"),
        ("CAGR", f"{m['cagr'] * 100:.2f}%"),
        ("Sharpe", f"{m['sharpe']:.3f}"),
        ("Sortino", f"{m['sortino']:.3f}"),
        ("Calmar", f"{m['calmar']:.3f}"),
        ("Max drawdown", f"{m['max_drawdown'] * 100:.2f}%"),
        ("Win rate", f"{m['win_rate'] * 100:.2f}%"),
        ("Profit factor", f"{m['profit_factor']:.3f}"),
        ("Expectancy ($)", f"{m['expectancy']:.4f}"),
        (
            "Fees / slippage",
            f"{result.fee_bps:.1f} bps / {result.slippage_bps:.1f} bps per side",
        ),
    ]
    table = "\n".join([f"| {k} | {v} |" for k, v in rows])
    return (
        f"# {title}\n\n"
        f"| metric | value |\n|---|---|\n{table}\n\n"
        "> Paper-trade for months before considering anything beyond research.\n"
    )
