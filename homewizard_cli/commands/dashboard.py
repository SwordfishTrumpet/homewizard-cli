import asyncio
from collections import deque

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..client_factory import API_VERSIONS, resolve_client
from ..config import resolve_host
from ..models import Measurement
from ..storage import _setup_store

app = typer.Typer()

SPARKLINE_CHARS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def _render_sparkline(values: list[float]) -> str:
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    chars = []
    for v in values:
        idx = int((v - mn) / rng * (len(SPARKLINE_CHARS) - 1))
        chars.append(SPARKLINE_CHARS[idx])
    return "".join(chars)


def _make_power_table(data: Measurement) -> Table:
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("Field", style="cyan", no_wrap=True)
    t.add_column("Value", style="green")
    direction = "exporting" if data.active_power_w < 0 else "importing"
    t.add_row("Power", f"{data.active_power_w} W ({direction})")
    if data.active_power_l1_w is not None:
        t.add_row("L1", f"{data.active_power_l1_w} W")
    if data.active_voltage_l1_v is not None:
        t.add_row("Voltage", f"{data.active_voltage_l1_v} V")
    if data.active_current_l1_a is not None:
        t.add_row("Current", f"{data.active_current_l1_a} A")
    return t


def _make_energy_table(data: Measurement) -> Table:
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("Field", style="cyan", no_wrap=True)
    t.add_column("Value", style="green")
    t.add_row("Import", f"{data.total_power_import_kwh:,.2f} kWh")
    t.add_row("Export", f"{data.total_power_export_kwh:,.2f} kWh")
    net = data.total_power_import_kwh - data.total_power_export_kwh
    t.add_row("Net", f"{net:,.2f} kWh")
    return t


def _make_gas_panel(data: Measurement) -> Panel:
    if data.total_gas_m3 is not None:
        text = Text(f"{data.total_gas_m3:,.2f} m³", style="green")
    else:
        text = Text("No gas meter", style="yellow")
    return Panel(text, title="Gas")


@app.callback(invoke_without_command=True)
def dashboard(
    watch: float = typer.Option(
        2.0, "--watch", "-w", help="Update interval in seconds"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
    db: str | None = typer.Option(
        None, "--db", help="SQLite database path for historical storage"
    ),
):
    """Live dashboard with Rich TUI."""
    asyncio.run(
        _dashboard_async(
            watch,
            host,
            timeout,
            proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            db=db,
        )
    )


async def _dashboard_async(
    watch: float,
    host: str | None,
    request_timeout: float,
    proxy: str | None = None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
    db: str | None = None,
):
    console = Console()
    host = resolve_host(host)
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="sparkline", size=3),
    )
    layout["main"].split_row(
        Layout(name="power"),
        Layout(name="energy"),
        Layout(name="gas", size=20),
    )

    sparkline_data: deque[float] = deque(maxlen=40)
    client = resolve_client(
        api_version,
        host,
        request_timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )

    async with client as c:
        store, serial = await _setup_store(db, api_version, c)
        try:
            with Live(layout, console=console, refresh_per_second=4, screen=True):
                try:
                    while True:
                        if api_version == "v2":
                            data = await c.get_json_v2("/api/measurement", Measurement)
                        else:
                            data = await c.get_json("/api/v1/data", Measurement)

                        if store and serial:
                            store.append(data.model_dump(), serial)

                        sparkline_data.append(data.active_power_w)

                        header_text = (
                            f"P1 Meter \u2014 {data.meter_model}  |  "
                            f"WiFi: {data.wifi_ssid} ({data.wifi_strength}%)"
                        )
                        layout["header"].update(
                            Panel(
                                header_text,
                                style="bold white on blue",
                            )
                        )
                        layout["main"]["power"].update(
                            Panel(_make_power_table(data), title="Power")
                        )
                        layout["main"]["energy"].update(
                            Panel(_make_energy_table(data), title="Energy")
                        )
                        layout["main"]["gas"].update(_make_gas_panel(data))
                        layout["sparkline"].update(
                            Panel(
                                _render_sparkline(list(sparkline_data)),
                                title=(
                                    f"Power Sparkline (last {len(sparkline_data)} "
                                    "samples)"
                                ),
                            )
                        )

                        await asyncio.sleep(watch)
                except asyncio.CancelledError:
                    pass
        except KeyboardInterrupt:
            pass
        finally:
            if store:
                store.close()
