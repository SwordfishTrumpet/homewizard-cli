"""TSV output formatter."""

from datetime import datetime
from rich.console import Console
from homewizard_cli.models import DataResponse


def write_tsv(data: DataResponse, console: Console):
    """Output data as TSV."""
    fields = [
        "timestamp",
        "active_power_w",
        "active_voltage_l1_v",
        "total_power_import_kwh",
        "total_power_export_kwh",
        "total_gas_m3",
    ]
    values = [
        datetime.now().isoformat(),
        str(data.active_power_w),
        str(data.active_voltage_l1_v) if data.active_voltage_l1_v is not None else "",
        str(data.total_power_import_kwh),
        str(data.total_power_export_kwh),
        str(data.total_gas_m3) if data.total_gas_m3 is not None else "",
    ]
    console.print("\t".join(fields))
    console.print("\t".join(values))
