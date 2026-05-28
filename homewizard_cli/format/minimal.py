"""Minimal one-liner output formatter."""

from rich.console import Console
from homewizard_cli.models import DataResponse
from ..util import format_p1_timestamp


def write_minimal(data: DataResponse, console: Console):
    """Output data as a minimal human-readable one-liner."""
    parts = [f"{data.active_power_w} W"]

    if data.active_voltage_l1_v is not None:
        parts.append(f"{data.active_voltage_l1_v} V")

    parts.append(f"{data.total_power_import_kwh} kWh in")
    parts.append(f"{data.total_power_export_kwh} kWh out")

    if data.total_gas_m3 is not None:
        parts.append(f"{data.total_gas_m3} m³ gas")

    console.print(" | ".join(parts))
