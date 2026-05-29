"""Raw DSMR telegram formatter (reconstructed from API data)."""

from rich.console import Console
from homewizard_cli.models import DataResponse
from ..util import _crc16


def write_raw(data: DataResponse, console: Console):
    """Output raw DSMR telegram reconstructed from available API data."""
    lines = [f"/{data.meter_model}"]
    lines.append("")
    lines.append(f"1-3:0.2.8({data.smr_version})")
    lines.append(f"0-0:96.1.1({data.unique_id})")
    lines.append(f"1-0:1.8.1({data.total_power_import_t1_kwh:06.3f}*kWh)")
    lines.append(f"1-0:1.8.2({data.total_power_import_t2_kwh:06.3f}*kWh)")
    if data.total_power_import_t3_kwh is not None:
        lines.append(f"1-0:1.8.3({data.total_power_import_t3_kwh:06.3f}*kWh)")
    if data.total_power_import_t4_kwh is not None:
        lines.append(f"1-0:1.8.4({data.total_power_import_t4_kwh:06.3f}*kWh)")
    lines.append(f"1-0:2.8.1({data.total_power_export_t1_kwh:06.3f}*kWh)")
    lines.append(f"1-0:2.8.2({data.total_power_export_t2_kwh:06.3f}*kWh)")
    if data.total_power_export_t3_kwh is not None:
        lines.append(f"1-0:2.8.3({data.total_power_export_t3_kwh:06.3f}*kWh)")
    if data.total_power_export_t4_kwh is not None:
        lines.append(f"1-0:2.8.4({data.total_power_export_t4_kwh:06.3f}*kWh)")
    tariff = "0001" if data.active_tariff == 1 else "0002"
    lines.append(f"0-0:96.14.0({tariff})")
    if data.active_power_w >= 0:
        lines.append(f"1-0:1.7.0({data.active_power_w:06.3f}*kW)")
    else:
        lines.append(f"1-0:2.7.0({abs(data.active_power_w):06.3f}*kW)")
    if data.active_power_l1_w is not None:
        val = abs(data.active_power_l1_w)
        if data.active_power_l1_w >= 0:
            lines.append(f"1-0:21.7.0({val:06.3f}*kW)")
        else:
            lines.append(f"1-0:22.7.0({val:06.3f}*kW)")
    if data.active_power_l2_w is not None:
        val = abs(data.active_power_l2_w)
        if data.active_power_l2_w >= 0:
            lines.append(f"1-0:41.7.0({val:06.3f}*kW)")
        else:
            lines.append(f"1-0:42.7.0({val:06.3f}*kW)")
    if data.active_power_l3_w is not None:
        val = abs(data.active_power_l3_w)
        if data.active_power_l3_w >= 0:
            lines.append(f"1-0:61.7.0({val:06.3f}*kW)")
        else:
            lines.append(f"1-0:62.7.0({val:06.3f}*kW)")
    if data.active_voltage_l1_v is not None:
        lines.append(f"1-0:32.7.0({data.active_voltage_l1_v}*V)")
    if data.active_voltage_l2_v is not None:
        lines.append(f"1-0:52.7.0({data.active_voltage_l2_v}*V)")
    if data.active_voltage_l3_v is not None:
        lines.append(f"1-0:72.7.0({data.active_voltage_l3_v}*V)")
    if data.active_current_l1_a is not None:
        lines.append(f"1-0:31.7.0({abs(data.active_current_l1_a):03.3f}*A)")
    if data.active_current_l2_a is not None:
        lines.append(f"1-0:51.7.0({abs(data.active_current_l2_a):03.3f}*A)")
    if data.active_current_l3_a is not None:
        lines.append(f"1-0:71.7.0({abs(data.active_current_l3_a):03.3f}*A)")
    if data.active_frequency_hz is not None:
        lines.append(f"1-0:14.7.0({data.active_frequency_hz:05.3f}*Hz)")
    if data.voltage_sag_l1_count is not None:
        lines.append(f"1-0:32.32.0({data.voltage_sag_l1_count:05d})")
    if data.voltage_sag_l2_count is not None:
        lines.append(f"1-0:52.32.0({data.voltage_sag_l2_count:05d})")
    if data.voltage_sag_l3_count is not None:
        lines.append(f"1-0:72.32.0({data.voltage_sag_l3_count:05d})")
    if data.voltage_swell_l1_count is not None:
        lines.append(f"1-0:32.36.0({data.voltage_swell_l1_count:05d})")
    if data.voltage_swell_l2_count is not None:
        lines.append(f"1-0:52.36.0({data.voltage_swell_l2_count:05d})")
    if data.voltage_swell_l3_count is not None:
        lines.append(f"1-0:72.36.0({data.voltage_swell_l3_count:05d})")
    if data.any_power_fail_count is not None:
        lines.append(f"0-0:96.7.21({data.any_power_fail_count:05d})")
    if data.long_power_fail_count is not None:
        lines.append(f"0-0:96.7.9({data.long_power_fail_count:05d})")
    if data.total_gas_m3 is not None and data.gas_unique_id:
        lines.append("0-1:24.1.0(003)")
        lines.append(f"0-1:96.1.0({data.gas_unique_id})")
        lines.append(f"0-1:24.2.1(0000000000W)({data.total_gas_m3:06.3f}*m3)")
    if data.active_power_average_w is not None:
        lines.append(f"1-0:15.7.0({data.active_power_average_w:06.3f}*kW)")
    if data.montly_power_peak_w is not None:
        lines.append(f"1-0:16.7.0({data.montly_power_peak_w:06.3f}*kW)")
    if data.text_message:
        lines.append(f"0-0:96.13.0({data.text_message})")
    lines.append("!")
    telegram_text = "\n".join(lines)
    crc_val = _crc16(telegram_text.rstrip("!").encode("ascii"))
    telegram_text += f"{crc_val:04X}"
    console.print(telegram_text)
