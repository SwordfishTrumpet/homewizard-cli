"""Client resolution and v2→v1 data conversion for homewizard-cli."""

from datetime import datetime

from .client import P1Client
from .client_v2 import P1ClientV2
from .models import DataResponse, ExternalDevice
from .models.v2 import MeasurementV2

API_VERSIONS = ["v1", "v2"]


def _iso_to_compact_timestamp(iso_str: str | None) -> int | None:
    """Convert ISO 8601 timestamp to v1 compact YYMMDDhhmmss int."""
    if not iso_str:
        return None
    try:
        dt = datetime.strptime(iso_str[:19], "%Y-%m-%dT%H:%M:%S")
        return int(dt.strftime("%y%m%d%H%M%S"))
    except Exception:
        return None


def resolve_client(
    api_version: str,
    host: str,
    timeout: float = 3.0,
    token: str | None = None,
    verify_cert: bool = True,
    proxy: str | None = None,
) -> P1Client | P1ClientV2:
    """Return the appropriate client for the given API version."""
    if api_version == "v2":
        return P1ClientV2(
            host, timeout, token=token, verify_cert=verify_cert, proxy=proxy
        )
    return P1Client(host, timeout, proxy=proxy)


def convert_v2_measurement(m: MeasurementV2) -> DataResponse:
    """Convert a v2 MeasurementV2 to the v1 DataResponse format.

    Some fields (wifi_ssid, wifi_strength, text_message) have no v2
    equivalent in the measurement endpoint — they are set to empty defaults.
    """
    external = [
        ExternalDevice(
            unique_id=d.unique_id,
            type=d.type,
            timestamp=_iso_to_compact_timestamp(d.timestamp) or 0,
            value=d.value,
            unit=d.unit,
        )
        for d in m.external
    ]
    return DataResponse(
        wifi_ssid="",
        wifi_strength=0,
        smr_version=m.protocol_version or 0,
        meter_model=m.meter_model or "",
        unique_id=m.unique_id or "",
        active_tariff=m.tariff or 0,
        total_power_import_kwh=m.energy_import_kwh or 0.0,
        total_power_import_t1_kwh=m.energy_import_t1_kwh or 0.0,
        total_power_import_t2_kwh=m.energy_import_t2_kwh or 0.0,
        total_power_import_t3_kwh=m.energy_import_t3_kwh,
        total_power_import_t4_kwh=m.energy_import_t4_kwh,
        total_power_export_kwh=m.energy_export_kwh or 0.0,
        total_power_export_t1_kwh=m.energy_export_t1_kwh or 0.0,
        total_power_export_t2_kwh=m.energy_export_t2_kwh or 0.0,
        total_power_export_t3_kwh=m.energy_export_t3_kwh,
        total_power_export_t4_kwh=m.energy_export_t4_kwh,
        active_power_w=m.power_w or 0.0,
        active_power_l1_w=m.power_l1_w,
        active_power_l2_w=m.power_l2_w,
        active_power_l3_w=m.power_l3_w,
        active_voltage_l1_v=m.voltage_l1_v or m.voltage_v,
        active_voltage_l2_v=m.voltage_l2_v,
        active_voltage_l3_v=m.voltage_l3_v,
        active_current_a=m.current_a,
        active_current_l1_a=m.current_l1_a,
        active_current_l2_a=m.current_l2_a,
        active_current_l3_a=m.current_l3_a,
        active_frequency_hz=m.frequency_hz,
        voltage_sag_l1_count=m.voltage_sag_l1_count,
        voltage_sag_l2_count=m.voltage_sag_l2_count,
        voltage_sag_l3_count=m.voltage_sag_l3_count,
        voltage_swell_l1_count=m.voltage_swell_l1_count,
        voltage_swell_l2_count=m.voltage_swell_l2_count,
        voltage_swell_l3_count=m.voltage_swell_l3_count,
        any_power_fail_count=m.any_power_fail_count,
        long_power_fail_count=m.long_power_fail_count,
        active_power_average_w=m.average_power_15m_w,
        montly_power_peak_w=m.monthly_power_peak_w,
        montly_power_peak_timestamp=_iso_to_compact_timestamp(
            m.monthly_power_peak_timestamp
        ),
        total_gas_m3=m.total_gas_m3,
        gas_timestamp=_iso_to_compact_timestamp(m.gas_timestamp),
        gas_unique_id=m.gas_unique_id,
        external=external,
    )
