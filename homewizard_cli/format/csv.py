"""CSV output formatter."""

import csv
import io
from datetime import datetime
from rich.console import Console
from homewizard_cli.models import DataResponse


def write_csv(data: DataResponse, console: Console):
    """Output data as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "timestamp",
            "active_power_w",
            "active_voltage_l1_v",
            "total_power_import_kwh",
            "total_power_export_kwh",
            "total_gas_m3",
        ]
    )
    writer.writerow(
        [
            datetime.now().isoformat(),
            data.active_power_w,
            data.active_voltage_l1_v or "",
            data.total_power_import_kwh,
            data.total_power_export_kwh,
            data.total_gas_m3 or "",
        ]
    )
    console.print(output.getvalue().strip())
