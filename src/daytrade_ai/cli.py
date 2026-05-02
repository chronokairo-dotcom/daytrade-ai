"""Typer CLI for daytrade-ai."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import typer

from daytrade_ai import __version__
from daytrade_ai.analysis.patterns import analyze_patterns, render_markdown
from daytrade_ai.backtest.engine import BacktestEngine
from daytrade_ai.backtest.walk_forward import WalkForward
from daytrade_ai.config import get_settings
from daytrade_ai.data.ccxt_source import CCXTDataSource
from daytrade_ai.data.csv_source import CSVDataSource
from daytrade_ai.paper.broker import PaperBroker
from daytrade_ai.reporting.report import format_markdown_report, format_text_report
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
    """Print version."""
    typer.echo(f"daytrade-ai {__version__}")


@app.command("list-strategies")
def list_strategies_cmd() -> None:
    """List registered strategies."""
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
    """Fetch OHLCV via ccxt and cache to parquet."""
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
    output_dir: Path = typer.Option(Path("backtest-results"), "--output-dir"),
    output_md: Path | None = typer.Option(
        None,
        "--output-md",
        help="Write markdown report to this exact path (in addition to output-dir).",
    ),
) -> None:
    """Run a backtest and write a report."""
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
        fee_bps=fee_bps if fee_bps is not None else settings.fee_bps,
        slippage_bps=slippage_bps if slippage_bps is not None else settings.slippage_bps,
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
    symbol: str | None = typer.Option(None, "--symbol"),
    timeframe: str = typer.Option("1h", "--timeframe"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    exchange: str = typer.Option("binance", "--exchange"),
    csv: Path | None = typer.Option(None, "--csv"),
    fee_bps: float | None = typer.Option(None, "--fee-bps"),
    slippage_bps: float | None = typer.Option(None, "--slippage-bps"),
    output_md: Path | None = typer.Option(
        None, "--output-md", help="Write aggregated walk-forward markdown report to this path."
    ),
) -> None:
    """Walk-forward backtest."""
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
        fee_bps=fee_bps if fee_bps is not None else settings.fee_bps,
        slippage_bps=slippage_bps if slippage_bps is not None else settings.slippage_bps,
    )
    wf = WalkForward(engine=engine, folds=folds, train_ratio=train_ratio)
    result = wf.run(df, strat)
    typer.echo("Per-fold summary:")
    typer.echo(result.summary.to_string(index=False))
    typer.echo("\nAggregate:")
    for k, v in result.aggregate.items():
        typer.echo(f"  {k}: {v:.4f}")

    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Walk-forward :: {strategy} :: {symbol or (csv.stem if csv else 'asset')} :: {timeframe}",
            "",
            f"- folds: {folds}",
            f"- train_ratio: {train_ratio}",
            f"- bars: {len(df)}",
            f"- range: {df.index[0]} -> {df.index[-1]}",
            "",
            "## Per-fold",
            "",
            "```",
            result.summary.to_string(index=False),
            "```",
            "",
            "## Aggregate",
            "",
        ]
        for k, v in result.aggregate.items():
            lines.append(f"- **{k}**: {v:.4f}")
        output_md.write_text("\n".join(lines) + "\n")
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
        help="Reserved flag. Refused: this build is paper-only.",
        hidden=True,
    ),
) -> None:
    """Paper trading loop. Fetches latest bar, asks strategy for signal,
    simulates fills via PaperBroker. NEVER places real orders."""
    if enable_live_trading:
        # Hard refuse.
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
        fee_bps=settings.fee_bps,
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
                # Allocate ~99% of equity to maintain target signal direction.
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


def main() -> None:  # pragma: no cover - thin wrapper
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
        False, "--no-fetch", help="Use cached data only, don't hit the network."
    ),
) -> None:
    """Compute pattern report for a symbol and write markdown."""
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


if __name__ == "__main__":  # pragma: no cover
    main()
