from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from daytrade_ai import __version__
from daytrade_ai.analysis.patterns import analyze_patterns, render_markdown
from daytrade_ai.backtest.engine import BacktestEngine
from daytrade_ai.backtest.walk_forward import WalkForward, WindowMode
from daytrade_ai.config import get_settings
from daytrade_ai.data.ccxt_source import CCXTDataSource
from daytrade_ai.data.csv_source import CSVDataSource
from daytrade_ai.paper.broker import PaperBroker
from daytrade_ai.reporting.report import (
    format_markdown_report,
    format_text_report,
    format_walk_forward_report,
)
from daytrade_ai.strategies import get_strategy, list_strategies

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="daytrade-ai: paper-trading-only research toolkit. See REALITY-CHECK.md.",
)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )


@app.callback()
def _root(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    _setup_logging(verbose)


@app.command()
def version() -> None:
    typer.echo(f"daytrade-ai {__version__}")


@app.command("list-strategies")
def list_strategies_cmd() -> None:
    for name in list_strategies():
        typer.echo(name)


@app.command("fetch-data")
def fetch_data(
    symbol: str = typer.Option(..., "--symbol"),
    timeframe: str = typer.Option("1h", "--timeframe"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    exchange: str = typer.Option("binance", "--exchange"),
) -> None:
    settings = get_settings()
    src = CCXTDataSource(exchange=exchange, cache_dir=settings.cache_dir)
    df = src.fetch(symbol=symbol, timeframe=timeframe, since=since, until=until)
    typer.echo(f"Fetched {len(df)} rows for {symbol}@{exchange} {timeframe}.")
    if not df.empty:
        typer.echo(f"Range: {df.index[0]} -> {df.index[-1]}")


@app.command()
def backtest(
    strategy: str = typer.Option(..., "--strategy"),
    symbol: str | None = typer.Option(None, "--symbol"),
    timeframe: str = typer.Option("1h", "--timeframe"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    exchange: str = typer.Option("binance", "--exchange"),
    csv: Path | None = typer.Option(
        None,
        "--csv",
        help="Load OHLCV from a local CSV instead of ccxt (offline-friendly).",
    ),
    fee_bps: float | None = typer.Option(None, "--fee-bps"),
    slippage_bps: float | None = typer.Option(None, "--slippage-bps"),
    initial_cash: float | None = typer.Option(None, "--initial-cash"),
    zero_cost: bool = typer.Option(
        False,
        "--zero-cost",
        help="Set fees and slippage to 0 for sanity check.",
    ),
    maker_fee_bps: float | None = typer.Option(None, "--maker-fee-bps"),
    use_taker_fee: bool = typer.Option(True, "--use-taker-fee"),
    output_dir: Path = typer.Option(Path("backtest-results"), "--output-dir"),
    output_md: Path | None = typer.Option(
        None,
        "--output-md",
        help="Write markdown report to this exact path (in addition to output-dir).",
    ),
) -> None:
    settings = get_settings()
    if csv is not None:
        df = CSVDataSource(csv).fetch(symbol or csv.stem, timeframe, since=since, until=until)
        symbol = symbol or csv.stem
    else:
        if symbol is None:
            raise typer.BadParameter("--symbol is required unless --csv is provided")
        df = CCXTDataSource(exchange=exchange, cache_dir=settings.cache_dir).fetch(
            symbol=symbol, timeframe=timeframe, since=since, until=until
        )

    if df.empty:
        typer.echo("No data fetched; aborting.", err=True)
        raise typer.Exit(code=1)

    strat = get_strategy(strategy)
    engine = BacktestEngine(
        initial_cash=initial_cash if initial_cash is not None else settings.initial_cash,
        fee_bps=fee_bps if fee_bps is not None else settings.taker_fee_bps,
        slippage_bps=slippage_bps if slippage_bps is not None else settings.slippage_bps,
        maker_fee_bps=maker_fee_bps if maker_fee_bps is not None else settings.maker_fee_bps,
        use_taker_fee=use_taker_fee if not zero_cost else settings.use_taker_fee,
        zero_cost_mode=zero_cost,
    )
    result = engine.run(df, strat)

    title = f"{strategy} :: {symbol} :: {timeframe}"
    text = format_text_report(result, title=title)
    md = format_markdown_report(result, title=title)
    typer.echo(text)

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_symbol = (symbol or "asset").replace("/", "-")
    base = output_dir / f"{stamp}__{strategy}__{safe_symbol}__{timeframe}"
    base.with_suffix(".txt").write_text(text)
    base.with_suffix(".md").write_text(md)
    result.equity_curve.to_csv(base.with_suffix(".equity.csv"))
    with base.with_suffix(".metrics.json").open("w") as f:
        json.dump(result.metrics, f, indent=2)
    typer.echo(f"\nReports written to: {base}.{{txt,md,equity.csv,metrics.json}}")
    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md)
        typer.echo(f"Markdown report also written to: {output_md}")


@app.command("walk-forward")
def walk_forward_cmd(
    strategy: str = typer.Option(..., "--strategy"),
    folds: int = typer.Option(5, "--folds"),
    train_ratio: float = typer.Option(0.5, "--train-ratio"),
    window_mode: str = typer.Option(
        "fixed",
        "--window-mode",
        help="fixed | expanding | rolling",
    ),
    step_size: int | None = typer.Option(None, "--step-size", help="Bars per fold (default: auto)"),
    benchmark: bool = typer.Option(
        True,
        "--benchmark/--no-benchmark",
        help="Include buy-and-hold benchmark comparison.",
    ),
    symbol: str | None = typer.Option(None, "--symbol"),
    timeframe: str = typer.Option("1h", "--timeframe"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    exchange: str = typer.Option("binance", "--exchange"),
    csv: Path | None = typer.Option(None, "--csv"),
    fee_bps: float | None = typer.Option(None, "--fee-bps"),
    slippage_bps: float | None = typer.Option(None, "--slippage-bps"),
    zero_cost: bool = typer.Option(False, "--zero-cost"),
    output_md: Path | None = typer.Option(
        None,
        "--output-md",
        help="Write aggregated walk-forward markdown report to this path.",
    ),
) -> None:
    settings = get_settings()
    if csv is not None:
        df = CSVDataSource(csv).fetch(symbol or csv.stem, timeframe, since=since, until=until)
    else:
        if symbol is None:
            raise typer.BadParameter("--symbol is required unless --csv is provided")
        df = CCXTDataSource(exchange=exchange, cache_dir=settings.cache_dir).fetch(
            symbol=symbol, timeframe=timeframe, since=since, until=until
        )

    strat = get_strategy(strategy)
    engine = BacktestEngine(
        initial_cash=settings.initial_cash,
        fee_bps=fee_bps if fee_bps is not None else settings.taker_fee_bps,
        slippage_bps=slippage_bps if slippage_bps is not None else settings.slippage_bps,
        zero_cost_mode=zero_cost,
    )

    _mode = {
        "fixed": WindowMode.FIXED,
        "expanding": WindowMode.EXPANDING,
        "rolling": WindowMode.ROLLING,
    }
    wm = _mode.get(window_mode, WindowMode.FIXED)

    bench_strat = get_strategy("buy_and_hold") if benchmark else None

    wf = WalkForward(
        engine=engine,
        folds=folds,
        train_ratio=train_ratio,
        window_mode=wm,
        step_size=step_size,
        benchmark_strategy=bench_strat,
    )
    result = wf.run(df, strat)
    typer.echo("Per-fold summary:")
    typer.echo(result.summary.to_string(index=False))
    typer.echo("\nAggregate:")
    for k, v in result.aggregate.items():
        typer.echo(f"  {k}: {v:.4f}")

    if result.bootstrap_ci is not None:
        lo, hi = result.bootstrap_ci
        typer.echo(f"\nSharpe 95% CI (bootstrap): ({lo:.3f}, {hi:.3f})")
        typer.echo(f"CI includes zero? {'YES — no edge detected' if lo <= 0 <= hi else 'NO'}")

    if result.benchmark_summary is not None:
        typer.echo("\nBenchmark (buy & hold) summary:")
        typer.echo(result.benchmark_summary.to_string(index=False))

    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        report = format_walk_forward_report(result, title=f"Walk-forward :: {strategy}")
        output_md.write_text(report)
        typer.echo(f"\nMarkdown report written to: {output_md}")


@app.command()
def paper(
    strategy: str = typer.Option(..., "--strategy"),
    symbol: str = typer.Option(..., "--symbol"),
    timeframe: str = typer.Option("1h", "--timeframe"),
    exchange: str = typer.Option("binance", "--exchange"),
    poll_seconds: int = typer.Option(60, "--poll-seconds"),
    iterations: int = typer.Option(0, "--iterations", help="0 = run forever"),
    enable_live_trading: bool = typer.Option(
        False,
        "--enable-live-trading",
        hidden=True,
    ),
) -> None:
    if enable_live_trading:
        typer.echo(
            "ERROR: --enable-live-trading is reserved and not implemented. "
            "This build is paper-only. See REALITY-CHECK.md.",
            err=True,
        )
        raise typer.Exit(code=2)

    settings = get_settings()
    if settings.enable_live_trading:
        typer.echo(
            "ERROR: settings.enable_live_trading=True but no live broker is available. "
            "Refusing to start.",
            err=True,
        )
        raise typer.Exit(code=2)

    src = CCXTDataSource(exchange=exchange, cache_dir=settings.cache_dir)
    strat = get_strategy(strategy)
    broker = PaperBroker(
        symbol=symbol,
        initial_cash=settings.initial_cash,
        fee_bps=settings.taker_fee_bps,
        slippage_bps=settings.slippage_bps,
    )
    typer.echo(f"[paper] strategy={strategy} symbol={symbol} timeframe={timeframe}")
    typer.echo("[paper] PAPER ONLY -- no real orders will be placed.")

    i = 0
    while iterations == 0 or i < iterations:
        i += 1
        try:
            df = src.fetch(symbol=symbol, timeframe=timeframe)
            if df.empty:
                typer.echo("[paper] empty data, sleeping")
            else:
                signals = strat.generate_signals(df)
                latest_signal = int(signals.iloc[-1])
                last_close = float(df["close"].iloc[-1])
                equity = broker.equity(last_close)
                if latest_signal == 0:
                    target_units = 0.0
                else:
                    target_units = latest_signal * (equity * 0.99) / last_close
                fill = broker.target_position(target_units, ref_price=last_close)
                typer.echo(
                    f"[paper] iter={i} signal={latest_signal} "
                    f"close={last_close:.2f} equity={equity:.2f} fill={fill}"
                )
        except Exception as e:
            typer.echo(f"[paper] error: {e}", err=True)
        if iterations != 0 and i >= iterations:
            break
        time.sleep(poll_seconds)


def main() -> None:
    app()


@app.command("analyze-patterns")
def analyze_patterns_cmd(
    symbol: str = typer.Option(..., "--symbol"),
    timeframe: str = typer.Option("1h", "--timeframe"),
    lookback_bars: int = typer.Option(720, "--lookback-bars"),
    exchange: str = typer.Option("binance", "--exchange"),
    csv: Path | None = typer.Option(None, "--csv"),
    output_dir: Path = typer.Option(Path("reports/patterns"), "--output-dir"),
    output_md: Path | None = typer.Option(None, "--output-md"),
    no_fetch: bool = typer.Option(
        False,
        "--no-fetch",
        help="Use cached data only, don't hit the network.",
    ),
) -> None:
    settings = get_settings()
    if csv is not None:
        df = CSVDataSource(csv).fetch(symbol, timeframe)
    else:
        src = CCXTDataSource(exchange=exchange, cache_dir=settings.cache_dir)
        if no_fetch:
            from daytrade_ai.data.cache import cache_path, read_cache

            df_opt = read_cache(cache_path(settings.cache_dir, exchange, symbol, timeframe))
            if df_opt is None or df_opt.empty:
                typer.echo("No cached data and --no-fetch set; aborting.", err=True)
                raise typer.Exit(code=1)
            df = df_opt
        else:
            df = src.fetch(symbol=symbol, timeframe=timeframe)
    if df.empty:
        typer.echo("No data; aborting.", err=True)
        raise typer.Exit(code=1)
    if lookback_bars > 0:
        df = df.tail(lookback_bars)

    rep = analyze_patterns(df, symbol=symbol, timeframe=timeframe)
    md = render_markdown(rep, generated_at=datetime.now(tz=UTC))
    typer.echo(md)

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace("/", "-")
    utcdate = datetime.now(tz=UTC).strftime("%Y%m%d")
    default_path = output_dir / f"{safe_symbol}__{timeframe}__{utcdate}.md"
    default_path.write_text(md)
    typer.echo(f"Wrote: {default_path}")
    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md)
        typer.echo(f"Also wrote: {output_md}")

    _append_history(rep)


def _append_history(rep: object) -> None:
    from daytrade_ai.analysis.patterns import PatternReport

    if not isinstance(rep, PatternReport):
        return
    history_dir = Path("reports/patterns")
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / "history.jsonl"
    record = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "symbol": rep.symbol,
        "timeframe": rep.timeframe,
        "adx": rep.adx_value,
        "rsi": rep.rsi_14,
        "atr_pct": rep.atr_pct_of_price,
        "atr_bucket": rep.atr_percentile_bucket,
        "trend_regime": rep.trend_regime,
        "zscore": rep.zscore_close_sma20,
        "close": rep.last_close,
    }
    with history_path.open("a") as f:
        f.write(json.dumps(record) + "\n")


@app.command("pattern-trend")
def pattern_trend_cmd(
    symbol: str | None = typer.Option(None, "--symbol"),
    n: int = typer.Option(30, "--n", help="Number of recent history entries to plot"),
) -> None:

    history_path = Path("reports/patterns/history.jsonl")
    if not history_path.exists():
        typer.echo("No history found at reports/patterns/history.jsonl", err=True)
        raise typer.Exit(code=1)

    records: list[dict[str, Any]] = []
    with history_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if symbol:
        records = [r for r in records if r.get("symbol") == symbol]

    if not records:
        typer.echo("No matching history entries.", err=True)
        raise typer.Exit(code=1)

    records = records[-n:]

    def _sparkline(values: list[float], width: int = 20) -> str:
        if not values:
            return "(empty)"
        lo, hi = min(values), max(values)
        span = hi - lo or 1.0
        chars = "▁▂▃▄▅▆▇█"
        return "".join(
            chars[min(int((v - lo) / span * (len(chars) - 1)), len(chars) - 1)]
            for v in values[-width:]
        )

    adx_vals = [float(r["adx"]) for r in records]
    rsi_vals = [float(r["rsi"]) for r in records]
    atr_vals = [float(r["atr_pct"]) for r in records]
    zscore_vals = [float(r["zscore"]) for r in records]

    typer.echo(f"\nPattern trend (last {len(records)} snapshots):\n")
    typer.echo(f"  Symbol: {records[-1].get('symbol', '?')} ({records[0].get('timeframe', '?')})")
    typer.echo(f"  Range: {records[0]['timestamp'][:10]} → {records[-1]['timestamp'][:10]}")
    typer.echo("")
    typer.echo(f"  ADX(14):     {_sparkline(adx_vals)}  (last: {adx_vals[-1]:.1f})")
    typer.echo(f"  RSI(14):     {_sparkline(rsi_vals)}  (last: {rsi_vals[-1]:.1f})")
    typer.echo(f"  ATR%/price:  {_sparkline(atr_vals)}  (last: {atr_vals[-1] * 100:.2f}%)")
    typer.echo(f"  Z-score:     {_sparkline(zscore_vals)}  (last: {zscore_vals[-1]:.2f})")
    typer.echo("")


if __name__ == "__main__":
    main()
