"""homewizard-cli energy command."""

import asyncio

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse

app = typer.Typer()


@app.callback(invoke_without_command=True)
def energy(
    tariffs: bool = typer.Option(False, "--tariffs", help="Show tariff breakdown"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str = typer.Option(None, "--proxy", help="HTTP proxy URL"),
):
    """Display cumulative energy readings."""
    asyncio.run(_energy_async(tariffs, host, timeout, proxy))


async def _energy_async(tariffs, host, timeout, proxy):
    console = Console()
    async with P1Client(host, timeout, proxy=proxy) as client:
        data = await client.get_json("/api/v1/data", DataResponse)

        net = data.total_power_import_kwh - data.total_power_export_kwh
        direction = "consumed" if net >= 0 else "produced"

        console.print(f"Import:  {data.total_power_import_kwh:,.2f} kWh")
        console.print(f"Export:  {data.total_power_export_kwh:,.2f} kWh")
        console.print(f"Net:     {abs(net):,.2f} kWh {direction}")

        if tariffs:
            console.print("")
            console.print(
                f"T1 (peak):     Import: {data.total_power_import_t1_kwh:,.2f}  Export: {data.total_power_export_t1_kwh:,.2f}"
            )
            console.print(
                f"T2 (off-peak): Import: {data.total_power_import_t2_kwh:,.2f}  Export: {data.total_power_export_t2_kwh:,.2f}"
            )
