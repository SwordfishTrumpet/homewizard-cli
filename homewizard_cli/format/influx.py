"""InfluxDB line protocol formatter."""

from datetime import UTC, datetime

from rich.console import Console

from homewizard_cli.models import DataResponse


def _escape_tag(value: str) -> str:
    """Escape an InfluxDB tag value (LOW-9): commas, spaces, and '='."""
    return value.replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def write_influx(data: DataResponse, console: Console):
    """Output data as InfluxDB line protocol."""
    timestamp_ns = int(datetime.now(UTC).timestamp() * 1_000_000_000)
    serial = _escape_tag(data.unique_id or "")
    meter_model = _escape_tag(data.meter_model or "")
    tags_parts = ["device=HWE-P1"]
    if serial:
        tags_parts.append(f"serial={serial}")
    if meter_model:
        tags_parts.append(f"meter_model={meter_model}")
    tags = ",".join(tags_parts)
    fields = f"active_power_w={data.active_power_w}"
    if data.active_power_l2_w is not None:
        fields += f",active_power_l2_w={data.active_power_l2_w}"
    if data.active_power_l3_w is not None:
        fields += f",active_power_l3_w={data.active_power_l3_w}"
    if data.active_voltage_l1_v is not None:
        fields += f",active_voltage_l1_v={data.active_voltage_l1_v}"
    if data.active_voltage_l2_v is not None:
        fields += f",active_voltage_l2_v={data.active_voltage_l2_v}"
    if data.active_voltage_l3_v is not None:
        fields += f",active_voltage_l3_v={data.active_voltage_l3_v}"
    if data.active_frequency_hz is not None:
        fields += f",active_frequency_hz={data.active_frequency_hz}"
    fields += f",total_power_import_kwh={data.total_power_import_kwh}"
    fields += f",total_power_export_kwh={data.total_power_export_kwh}"
    if data.total_gas_m3 is not None:
        fields += f",total_gas_m3={data.total_gas_m3}"
    console.print(f"p1_meter,{tags} {fields} {timestamp_ns}", soft_wrap=True)
