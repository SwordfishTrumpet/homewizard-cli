"""Tests for client_factory.py."""

import ssl
from unittest.mock import patch

from homewizard_cli.client import P1Client
from homewizard_cli.client_factory import (
    convert_v2_measurement,
    resolve_client,
    to_measurement,
)
from homewizard_cli.client_v2 import P1ClientV2
from homewizard_cli.models import Measurement
from homewizard_cli.models.v2 import MeasurementV2, V2ExternalDevice

# ── resolve_client ────────────────────────────────────────────


def test_resolve_client_v2_returns_p1clientv2():
    """Test resolve_client returns P1ClientV2 for api_version='v2'."""
    with patch(
        "homewizard_cli.client_v2._create_ssl_context",
        return_value=ssl.create_default_context(),
    ):
        client = resolve_client("v2", "192.168.1.1", timeout=3.0)
    assert isinstance(client, P1ClientV2)
    assert client.host == "192.168.1.1"
    assert client.timeout == 3.0


def test_resolve_client_v2_with_token():
    """Test resolve_client passes token to P1ClientV2."""
    client = resolve_client("v2", "192.168.1.1", token="my_token", verify_cert=False)
    assert isinstance(client, P1ClientV2)
    assert client.token == "my_token"


def test_resolve_client_v1_returns_p1client():
    """Test resolve_client returns P1Client for api_version='v1'."""
    client = resolve_client("v1", "192.168.1.1", timeout=5.0)
    assert isinstance(client, P1Client)
    assert client.host == "192.168.1.1"
    assert client.timeout == 5.0


def test_resolve_client_v1_with_proxy():
    """Test resolve_client passes proxy to P1Client."""
    client = resolve_client("v1", "192.168.1.1", proxy="http://proxy:8080")
    assert isinstance(client, P1Client)


# ── to_measurement ───────────────────────────────────────────


def test_to_measurement_from_v2_dict():
    """Test to_measurement converts a plain v2 dict to Measurement."""
    raw = {
        "power_w": 1500.0,
        "energy_import_kwh": 1234.5,
        "energy_export_kwh": 0.0,
        "tariff": 1,
        "protocol_version": 50,
    }
    m = to_measurement(raw, api_version="v2")
    assert isinstance(m, Measurement)
    assert m.active_power_w == 1500.0
    assert m.total_power_import_kwh == 1234.5
    assert m.total_power_export_kwh == 0.0
    assert m.active_tariff == 1
    assert m.smr_version == 50


def test_to_measurement_from_v2_dict_with_all_optional_fields():
    """Test to_measurement with a full v2 dict including all optional fields."""
    raw = {
        "power_w": 1500.0,
        "power_l1_w": 500.0,
        "power_l2_w": 600.0,
        "power_l3_w": 400.0,
        "energy_import_kwh": 1234.5,
        "energy_import_t1_kwh": 600.0,
        "energy_import_t2_kwh": 634.5,
        "energy_import_t3_kwh": 0.0,
        "energy_import_t4_kwh": 0.0,
        "energy_export_kwh": 50.0,
        "energy_export_t1_kwh": 20.0,
        "energy_export_t2_kwh": 30.0,
        "energy_export_t3_kwh": 0.0,
        "energy_export_t4_kwh": 0.0,
        "voltage_l1_v": 230.0,
        "voltage_l2_v": 231.0,
        "voltage_l3_v": 229.0,
        "current_a": 10.0,
        "current_l1_a": 3.0,
        "current_l2_a": 4.0,
        "current_l3_a": 3.0,
        "frequency_hz": 50.0,
        "average_power_15m_w": 1480.0,
        "monthly_power_peak_w": 3200.0,
        "monthly_power_peak_timestamp": "2025-05-29T12:00:00",
        "voltage_sag_l1_count": 1,
        "voltage_sag_l2_count": 2,
        "voltage_sag_l3_count": 0,
        "voltage_swell_l1_count": 0,
        "voltage_swell_l2_count": 1,
        "voltage_swell_l3_count": 0,
        "any_power_fail_count": 3,
        "long_power_fail_count": 1,
        "total_gas_m3": 7252.631,
        "gas_timestamp": "2025-05-29T12:00:00",
        "gas_unique_id": "gas123",
        "external": [
            {
                "unique_id": "ext1",
                "type": "gas_meter",
                "timestamp": "2025-05-29T12:00:00",
                "value": 1234.5,
                "unit": "m3",
            }
        ],
    }
    m = to_measurement(raw, api_version="v2")
    assert isinstance(m, Measurement)
    assert m.active_power_w == 1500.0
    assert m.active_power_l1_w == 500.0
    assert m.active_power_l2_w == 600.0
    assert m.active_power_l3_w == 400.0
    assert m.total_power_import_kwh == 1234.5
    assert m.total_power_import_t3_kwh == 0.0
    assert m.total_power_import_t4_kwh == 0.0
    assert m.total_power_export_kwh == 50.0
    assert m.total_power_export_t3_kwh == 0.0
    assert m.total_power_export_t4_kwh == 0.0
    assert m.active_voltage_l1_v == 230.0
    assert m.active_voltage_l2_v == 231.0
    assert m.active_voltage_l3_v == 229.0
    assert m.active_current_a == 10.0
    assert m.active_current_l1_a == 3.0
    assert m.active_current_l2_a == 4.0
    assert m.active_current_l3_a == 3.0
    assert m.active_frequency_hz == 50.0
    assert m.active_power_average_w == 1480.0
    assert m.monthly_power_peak_w == 3200.0
    assert m.monthly_power_peak_timestamp == 250529120000
    assert m.voltage_sag_l1_count == 1
    assert m.voltage_sag_l2_count == 2
    assert m.voltage_sag_l3_count == 0
    assert m.voltage_swell_l1_count == 0
    assert m.voltage_swell_l2_count == 1
    assert m.voltage_swell_l3_count == 0
    assert m.any_power_fail_count == 3
    assert m.long_power_fail_count == 1
    assert m.total_gas_m3 == 7252.631
    assert m.gas_timestamp == 250529120000
    assert m.gas_unique_id == "gas123"
    assert len(m.external) == 1
    assert m.external[0].unique_id == "ext1"
    assert m.external[0].type == "gas_meter"
    assert m.external[0].timestamp == 250529120000
    assert m.external[0].value == 1234.5
    assert m.external[0].unit == "m3"


def test_to_measurement_from_measurementv2_instance():
    """Test to_measurement accepts a MeasurementV2 pydantic instance."""
    v2 = MeasurementV2(
        power_w=2500.0,
        energy_import_kwh=5000.0,
        energy_export_kwh=100.0,
        tariff=2,
        protocol_version=50,
        meter_model="ISKRA TEST",
        unique_id="dev123",
    )
    m = to_measurement(v2)
    assert isinstance(m, Measurement)
    assert m.active_power_w == 2500.0
    assert m.total_power_import_kwh == 5000.0
    assert m.total_power_export_kwh == 100.0
    assert m.active_tariff == 2
    assert m.smr_version == 50
    assert m.meter_model == "ISKRA TEST"
    assert m.unique_id == "dev123"


def test_to_measurement_from_measurementv2_with_external_devices():
    """Test to_measurement with external devices from a MeasurementV2 instance."""
    v2 = MeasurementV2(
        power_w=1000.0,
        energy_import_kwh=100.0,
        external=[
            V2ExternalDevice(
                unique_id="water1",
                type="water_meter",
                timestamp="2025-05-29T10:30:00",
                value=456.7,
                unit="m3",
            ),
            V2ExternalDevice(
                unique_id="heat1",
                type="heat_meter",
                timestamp="2025-05-29T11:00:00",
                value=89.0,
                unit="GJ",
            ),
        ],
    )
    m = to_measurement(v2)
    assert len(m.external) == 2
    assert m.external[0].unique_id == "water1"
    assert m.external[0].timestamp == 250529103000
    assert m.external[1].unique_id == "heat1"
    assert m.external[1].timestamp == 250529110000


def test_to_measurement_from_v1_dict():
    """Test to_measurement passes through a v1 dict unchanged."""
    raw = {
        "active_power_w": 500.0,
        "total_power_import_kwh": 100.0,
        "total_power_export_kwh": 0.0,
        "active_tariff": 1,
        "smr_version": 50,
        "meter_model": "TEST",
        "unique_id": "abc",
        "wifi_ssid": "TestNet",
        "wifi_strength": 80,
    }
    m = to_measurement(raw, api_version="v1")
    assert isinstance(m, Measurement)
    assert m.active_power_w == 500.0
    assert m.total_power_import_kwh == 100.0
    assert m.wifi_ssid == "TestNet"
    assert m.wifi_strength == 80


def test_to_measurement_preserves_v1_timestamp_int():
    """Test that v1 compact timestamps are preserved as ints."""
    raw = {
        "active_power_w": 500.0,
        "total_power_import_kwh": 100.0,
        "gas_timestamp": 250529120000,
        "monthly_power_peak_timestamp": 250529120000,
    }
    m = to_measurement(raw, api_version="v2")
    assert m.gas_timestamp == 250529120000
    assert m.monthly_power_peak_timestamp == 250529120000


# ── convert_v2_measurement ───────────────────────────────────


def test_convert_v2_measurement_backward_compat():
    """Test convert_v2_measurement is a backward-compat wrapper."""
    v2 = MeasurementV2(
        power_w=3000.0,
        energy_import_kwh=9999.0,
        energy_export_kwh=0.0,
        tariff=1,
        protocol_version=50,
    )
    m = convert_v2_measurement(v2)
    assert isinstance(m, Measurement)
    assert m.active_power_w == 3000.0
    assert m.total_power_import_kwh == 9999.0
    assert m.total_power_export_kwh == 0.0
    assert m.active_tariff == 1
    assert m.smr_version == 50


def test_convert_v2_measurement_with_none_optional_fields():
    """Test convert_v2_measurement handles None optional fields."""
    v2 = MeasurementV2(
        power_w=0.0,
        energy_import_kwh=0.0,
        voltage_l1_v=None,
        current_l1_a=None,
        frequency_hz=None,
        total_gas_m3=None,
        gas_timestamp=None,
    )
    m = convert_v2_measurement(v2)
    assert m.active_voltage_l1_v is None
    assert m.active_current_l1_a is None
    assert m.active_frequency_hz is None
    assert m.total_gas_m3 is None
    assert m.gas_timestamp is None
