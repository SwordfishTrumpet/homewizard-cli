"""Shell export format formatter."""

from rich.console import Console
from homewizard_cli.models import DataResponse


def write_env(data: DataResponse, console: Console):
    """Output data as shell export statements."""
    mapping = {
        "P1_ACTIVE_POWER_W": data.active_power_w,
        "P1_ACTIVE_POWER_L2_W": data.active_power_l2_w,
        "P1_ACTIVE_POWER_L3_W": data.active_power_l3_w,
        "P1_ACTIVE_VOLTAGE_L1_V": data.active_voltage_l1_v,
        "P1_ACTIVE_VOLTAGE_L2_V": data.active_voltage_l2_v,
        "P1_ACTIVE_VOLTAGE_L3_V": data.active_voltage_l3_v,
        "P1_ACTIVE_FREQUENCY_HZ": data.active_frequency_hz,
        "P1_TOTAL_POWER_IMPORT_KWH": data.total_power_import_kwh,
        "P1_TOTAL_POWER_EXPORT_KWH": data.total_power_export_kwh,
        "P1_TOTAL_GAS_M3": data.total_gas_m3,
        "P1_WIFI_STRENGTH": data.wifi_strength,
        "P1_METER_MODEL": data.meter_model,
        "P1_SERIAL": data.unique_id,
    }
    for key, value in mapping.items():
        if value is not None:
            console.print(f"export {key}={value!r}")
