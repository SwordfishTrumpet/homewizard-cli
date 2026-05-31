"""TSV output formatter."""

from datetime import datetime

from rich.console import Console

from homewizard_cli.models import DataResponse


def write_tsv(data: DataResponse, console: Console):
    """Output data as TSV."""
    fields = [
        "timestamp",
        "active_power_w",
        "active_power_l2_w",
        "active_power_l3_w",
        "active_voltage_l1_v",
        "active_voltage_l2_v",
        "active_voltage_l3_v",
        "active_frequency_hz",
        "total_power_import_kwh",
        "total_power_export_kwh",
        "total_gas_m3",
    ]
    values = [
        datetime.now().isoformat(),
        str(data.active_power_w),
        str(data.active_power_l2_w) if data.active_power_l2_w is not None else "",
        str(data.active_power_l3_w) if data.active_power_l3_w is not None else "",
        str(data.active_voltage_l1_v) if data.active_voltage_l1_v is not None else "",
        str(data.active_voltage_l2_v) if data.active_voltage_l2_v is not None else "",
        str(data.active_voltage_l3_v) if data.active_voltage_l3_v is not None else "",
        str(data.active_frequency_hz) if data.active_frequency_hz is not None else "",
        str(data.total_power_import_kwh),
        str(data.total_power_export_kwh),
        str(data.total_gas_m3) if data.total_gas_m3 is not None else "",
    ]
    output = "\t".join(fields) + "\n" + "\t".join(values)
    console.file.write(output)
