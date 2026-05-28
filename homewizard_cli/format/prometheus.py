"""Prometheus exposition format formatter."""

from rich.console import Console
from homewizard_cli.models import DataResponse


def write_prometheus(data: DataResponse, console: Console):
    """Output data as Prometheus exposition format."""
    lines = [
        "# HELP p1_active_power_w Current active power in watts",
        "# TYPE p1_active_power_w gauge",
        f"p1_active_power_w {data.active_power_w}",
        "",
        "# HELP p1_total_power_import_kwh Total imported energy in kWh",
        "# TYPE p1_total_power_import_kwh counter",
        f"p1_total_power_import_kwh {data.total_power_import_kwh}",
        "",
        "# HELP p1_total_power_export_kwh Total exported energy in kWh",
        "# TYPE p1_total_power_export_kwh counter",
        f"p1_total_power_export_kwh {data.total_power_export_kwh}",
    ]
    if data.active_voltage_l1_v is not None:
        lines.extend(
            [
                "",
                "# HELP p1_active_voltage_l1_v Phase 1 voltage",
                "# TYPE p1_active_voltage_l1_v gauge",
                f"p1_active_voltage_l1_v {data.active_voltage_l1_v}",
            ]
        )
    if data.total_gas_m3 is not None:
        lines.extend(
            [
                "",
                "# HELP p1_total_gas_m3 Total gas consumption in m3",
                "# TYPE p1_total_gas_m3 counter",
                f"p1_total_gas_m3 {data.total_gas_m3}",
            ]
        )
    lines.append("")
    console.print("\n".join(lines))
