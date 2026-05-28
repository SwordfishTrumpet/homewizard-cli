"""Rich table output formatter."""

from rich.console import Console
from rich.table import Table
from homewizard_cli.models import DataResponse
from ..util import format_p1_timestamp


def write_table(data: DataResponse, console: Console):
    """Output data as a formatted table."""
    table = Table(
        title=f"P1 Meter — {data.meter_model}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    # Core fields
    table.add_row("WiFi", f"{data.wifi_ssid} ({data.wifi_strength}%)")
    table.add_row("DSMR", str(data.smr_version))
    table.add_row("Tariff", "Peak (T1)" if data.active_tariff == 1 else "Off-peak (T2)")
    table.add_row("Power", f"{data.active_power_w} W")

    if data.active_voltage_l1_v is not None:
        table.add_row("Voltage", f"{data.active_voltage_l1_v} V")
    if data.active_current_l1_a is not None:
        table.add_row("Current", f"{data.active_current_l1_a} A")

    table.add_row("Import Total", f"{data.total_power_import_kwh} kWh")
    table.add_row("Export Total", f"{data.total_power_export_kwh} kWh")

    if data.total_gas_m3 is not None:
        table.add_row("Gas", f"{data.total_gas_m3} m³")

    if data.gas_timestamp is not None:
        table.add_row("Gas Time", format_p1_timestamp(data.gas_timestamp))

    console.print(table)
