"""Raw DSMR telegram formatter."""

from rich.console import Console
from homewizard_cli.models import DataResponse


def write_raw(data: DataResponse, console: Console):
    """Output raw DSMR-style representation (from available data)."""
    lines = [f"/{data.meter_model}"]
    lines.append(f"1-3:0.2.8({data.smr_version})")
    tariff = "0001" if data.active_tariff == 1 else "0002"
    lines.append(f"0-0:96.14.0({tariff})")
    lines.append(f"1-0:1.8.1({data.total_power_import_t1_kwh:06.3f}*kWh)")
    lines.append(f"1-0:1.8.2({data.total_power_import_t2_kwh:06.3f}*kWh)")
    lines.append(f"1-0:2.8.1({data.total_power_export_t1_kwh:06.3f}*kWh)")
    lines.append(f"1-0:2.8.2({data.total_power_export_t2_kwh:06.3f}*kWh)")
    lines.append(f"1-0:1.7.0({data.active_power_w:06.3f}*kW)")
    if data.active_voltage_l1_v is not None:
        lines.append(f"1-0:32.7.0({data.active_voltage_l1_v}*V)")
    if data.total_gas_m3 is not None:
        lines.append(f"0-1:24.2.1({data.total_gas_m3:06.3f}*m3)")
    lines.append("!")
    console.print("\n".join(lines))
