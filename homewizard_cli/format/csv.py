"""CSV output formatter."""

import csv
import io
from datetime import UTC, datetime

from rich.console import Console

from homewizard_cli.models import DataResponse

from ..util import _meter_timestamp_with_offset


def _optional(value: float | None) -> str:
    """Render an optional number as a CSV field (empty when absent)."""
    return "" if value is None else str(value)


def write_csv(data: DataResponse, console: Console):
    """Output data as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "timestamp",
            "active_power_w",
            "active_power_l1_w",
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
            # The reading's own time when the meter reports one, else the moment
            # this row was written; both carry a UTC offset (issue #39, #40).
            _meter_timestamp_with_offset(data.timestamp)
            or datetime.now(UTC).isoformat(),
            data.active_power_w,
            _optional(data.active_power_l1_w),
            _optional(data.active_power_l2_w),
            _optional(data.active_power_l3_w),
            _optional(data.active_voltage_l1_v),
            _optional(data.active_voltage_l2_v),
            _optional(data.active_voltage_l3_v),
            _optional(data.active_frequency_hz),
            data.total_power_import_kwh,
            data.total_power_export_kwh,
            _optional(data.total_gas_m3),
        ]
    )
    console.print(output.getvalue().strip(), soft_wrap=True)
