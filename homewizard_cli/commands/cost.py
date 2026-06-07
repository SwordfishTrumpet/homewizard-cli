"""Cost command for homewizard-cli."""

import asyncio
from datetime import datetime, timedelta

import typer
from rich.console import Console
from rich.table import Table

from ..client_factory import resolve_client
from ..config import load_config, resolve_host
from ..config import TariffConfig
from ..util import _dumps_json
from ..cost import CostCalculator
from ..format import get_format
from ..storage import MeasurementStore

app = typer.Typer()


@app.callback(invoke_without_command=True)
def cost(
    ctx: typer.Context,
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    api_version: str = typer.Option("v2", "--api-version", help="API version"),
    token: str | None = typer.Option(None, "--token", help="API v2 token"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Disable SSL verification"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    format: str = typer.Option("auto", "--format", "-f", help="Output format"),
    watch: float | None = typer.Option(None, "--watch", help="Poll interval in seconds"),
    today: bool = typer.Option(False, "--today", help="Today's cost from DB"),
    yesterday: bool = typer.Option(False, "--yesterday", help="Yesterday's cost from DB"),
    this_month: bool = typer.Option(False, "--this-month", help="This month's cost from DB"),
    tariffs: bool = typer.Option(False, "--tariffs", help="Show tariff breakdown table"),
    db: str | None = typer.Option(None, "--db", help="SQLite database path"),
    t1_rate: float | None = typer.Option(None, "--t1-rate", help="T1 rate (€/kWh)"),
    t2_rate: float | None = typer.Option(None, "--t2-rate", help="T2 rate (€/kWh)"),
    t3_rate: float | None = typer.Option(None, "--t3-rate", help="T3 rate (€/kWh)"),
    t4_rate: float | None = typer.Option(None, "--t4-rate", help="T4 rate (€/kWh)"),
    export_credit: float | None = typer.Option(None, "--export-credit", help="Export credit (€/kWh)"),
    currency: str | None = typer.Option(None, "--currency", help="Currency symbol"),
):
    """Calculate energy costs from real-time or historical data."""
    asyncio.run(
        _cost_async(
            host=host,
            timeout=timeout,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            proxy=proxy,
            format=format,
            watch=watch,
            today=today,
            yesterday=yesterday,
            this_month=this_month,
            tariffs=tariffs,
            db=db,
            t1_rate=t1_rate,
            t2_rate=t2_rate,
            t3_rate=t3_rate,
            t4_rate=t4_rate,
            export_credit=export_credit,
            currency=currency,
        )
    )


async def _cost_async(
    host: str | None,
    timeout: float,
    api_version: str,
    token: str | None,
    no_verify: bool,
    proxy: str | None,
    format: str,
    watch: float | None,
    today: bool,
    yesterday: bool,
    this_month: bool,
    tariffs: bool,
    db: str | None,
    t1_rate: float | None,
    t2_rate: float | None,
    t3_rate: float | None,
    t4_rate: float | None,
    export_credit: float | None,
    currency: str | None,
) -> None:
    console = Console()
    output_format = get_format(format, console.is_terminal)

    # Resolve tariff config: CLI > config > defaults
    cfg = load_config()
    tariff_cfg = cfg.tariffs or TariffConfig()
    if t1_rate is not None:
        tariff_cfg.t1_rate = t1_rate
    if t2_rate is not None:
        tariff_cfg.t2_rate = t2_rate
    if t3_rate is not None:
        tariff_cfg.t3_rate = t3_rate
    if t4_rate is not None:
        tariff_cfg.t4_rate = t4_rate
    if export_credit is not None:
        tariff_cfg.export_credit = export_credit
    if currency is not None:
        tariff_cfg.currency = currency

    calc = CostCalculator(tariff_cfg)

    # Historical DB mode
    if today or yesterday or this_month:
        if not db:
            from pathlib import Path

            db = str(Path.home() / ".config" / "homewizard-cli" / "energy.db")
        store = MeasurementStore(db)
        now = datetime.now()
        start: datetime | None = None
        end: datetime | None = None

        if today:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif yesterday:
            yest = now - timedelta(days=1)
            start = yest.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif this_month:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now

        rows = store.query(start=start, end=end, fields=["total_power_import_kwh", "total_power_export_kwh", "active_tariff"])
        result = calc.calculate_history(rows)
        _write_cost(result, output_format, console, tariffs)
        store.close()
        return

    # Real-time mode
    resolved_host = resolve_host(host)
    client = resolve_client(
        api_version,
        resolved_host,
        timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )
    async with client as c:
        from ..models import Measurement

        if api_version == "v2":
            data = await c.get_json_v2("/api/measurement", Measurement)
        else:
            data = await c.get_json("/api/v1/data", Measurement)
        result = calc.calculate(data.model_dump())
        _write_cost(result, output_format, console, tariffs)

        if watch:
            while True:
                await asyncio.sleep(watch)
                if api_version == "v2":
                    data = await c.get_json_v2("/api/measurement", Measurement)
                else:
                    data = await c.get_json("/api/v1/data", Measurement)
                result = calc.calculate(data.model_dump())
                _write_cost(result, output_format, console, tariffs)


def _write_cost(result: dict, fmt: str, console: Console, show_tariffs: bool) -> None:
    if show_tariffs or fmt == "table":
        t = Table(show_header=True, header_style="bold magenta")
        t.add_column("Tariff", style="cyan")
        t.add_column("kWh", justify="right")
        t.add_column("Rate", justify="right")
        t.add_column("Cost", justify="right")
        currency = result.get("currency", "EUR")
        for i in range(1, 5):
            kwh = result.get(f"t{i}_import_kwh", 0)
            rate = result.get(f"t{i}_rate", 0)
            cost = result.get(f"t{i}_cost", 0)
            if kwh > 0 or rate > 0:
                t.add_row(f"T{i}", f"{kwh:,.3f}", f"{rate:.2f}{currency}", f"{cost:,.2f}{currency}")
        t.add_row(
            "Export",
            f"{result.get('total_export_kwh', 0):,.3f}",
            f"-{result.get('export_credit', 0):,.2f}{currency}",
            "",
            style="green",
        )
        t.add_row(
            "Total",
            "",
            "",
            f"{result.get('total_cost', 0):,.2f}{currency}",
            style="bold",
        )
        console.print(t)
    elif fmt == "json":
        console.print(_dumps_json(result, indent=True))
    else:
        console.print(f"Total cost: {result.get('total_cost', 0):,.2f} {result.get('currency', 'EUR')}")
