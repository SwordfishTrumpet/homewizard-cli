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
    )
    writer.writerow(
        [
            datetime.now().isoformat(),
            data.active_power_w,
            str(data.active_power_l2_w) if data.active_power_l2_w is not None else "",
            str(data.active_power_l3_w) if data.active_power_l3_w is not None else "",
            str(data.active_voltage_l1_v)
            if data.active_voltage_l1_v is not None
            else "",
            str(data.active_voltage_l2_v)
            if data.active_voltage_l2_v is not None
            else "",
            str(data.active_voltage_l3_v)
            if data.active_voltage_l3_v is not None
            else "",
            str(data.active_frequency_hz)
            if data.active_frequency_hz is not None
            else "",
            data.total_power_import_kwh,
            data.total_power_export_kwh,
            str(data.total_gas_m3) if data.total_gas_m3 is not None else "",
        ]
    )
    console.print(output.getvalue().strip())
