from pathlib import Path

from homewizard_cli.models import (
    BatteryState,
    DataResponse,
    DeviceInfoV2,
    ExternalDevice,
    Measurement,
    MeasurementV2,
    SystemResponse,
    SystemV2,
    TelegramV2,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_re_export_sanity():
    from homewizard_cli import models

    assert DataResponse is models.DataResponse
    assert SystemResponse is models.SystemResponse
    assert MeasurementV2 is models.MeasurementV2
    assert DeviceInfoV2 is models.DeviceInfoV2
    assert SystemV2 is models.SystemV2
    assert TelegramV2 is models.TelegramV2
    assert BatteryState is models.BatteryState
    assert Measurement is models.Measurement
    assert ExternalDevice is models.ExternalDevice


def test_data_response_from_fixture():
    with open(FIXTURES / "data.json") as f:
        data = DataResponse.model_validate_json(f.read())

    assert data.wifi_ssid == "Metta"
    assert data.wifi_strength == 100
    assert data.smr_version == 50
    assert data.meter_model == "ISKRA 2M550E-1011"
    assert data.active_tariff == 2
    assert data.total_power_import_kwh == 10201.212
    assert data.active_power_w == -106
    assert data.total_gas_m3 == 7252.631
    assert len(data.external) == 1
    assert data.external[0].type == "gas_meter"


def test_data_response_optional_fields():
    minimal = {
        "wifi_ssid": "Test",
        "wifi_strength": 50,
        "smr_version": 50,
        "meter_model": "TEST",
        "unique_id": "abc123",
        "active_tariff": 1,
        "total_power_import_kwh": 100.0,
        "total_power_import_t1_kwh": 50.0,
        "total_power_import_t2_kwh": 50.0,
        "total_power_export_kwh": 0.0,
        "total_power_export_t1_kwh": 0.0,
        "total_power_export_t2_kwh": 0.0,
        "active_power_w": 500.0,
    }
    data = DataResponse.model_validate(minimal)
    assert data.active_voltage_l1_v is None
    assert data.total_gas_m3 is None
    assert data.external == []


def test_system_response_from_fixture():
    with open(FIXTURES / "system.json") as f:
        system = SystemResponse.model_validate_json(f.read())
    assert system.cloud_enabled is True


def test_measurement_v2_from_fixture():
    with open(FIXTURES / "measurement_v2.json") as f:
        data = MeasurementV2.model_validate_json(f.read())
    assert data.protocol_version == 50
    assert data.meter_model == "ISKRA 2M550E-1011"
    assert data.tariff == 2
    assert data.power_w == -106
    assert data.total_gas_m3 == 9876.543
    assert len(data.external) == 1
    assert data.external[0].type == "gas_meter"


def test_device_info_v2_from_fixture():
    with open(FIXTURES / "device_v2.json") as f:
        data = DeviceInfoV2.model_validate_json(f.read())
    assert data.product_type == "HWE-P1"
    assert data.serial == "5c2faf3864e0"
    assert data.firmware_version == "6.0305"


def test_system_v2_from_fixture():
    with open(FIXTURES / "system_v2.json") as f:
        data = SystemV2.model_validate_json(f.read())
    assert data.cloud_enabled is True
    assert data.wifi_ssid == "Metta"


def test_telegram_v2_from_fixture():
    with open(FIXTURES / "telegram_v2.json") as f:
        data = TelegramV2.model_validate_json(f.read())
    assert "ISK5" in data.telegram


def test_battery_state_from_fixture():
    with open(FIXTURES / "battery_state.json") as f:
        data = BatteryState.model_validate_json(f.read())
    assert data.mode == "to_full"
    assert len(data.permissions) == 2


def test_measurement_from_v1_dict():
    data = Measurement.model_validate(
        {
            "wifi_ssid": "Test",
            "wifi_strength": 100,
            "smr_version": 50,
            "meter_model": "TEST",
            "unique_id": "abc",
            "active_tariff": 1,
            "total_power_import_kwh": 100.0,
            "total_power_import_t1_kwh": 50.0,
            "total_power_import_t2_kwh": 50.0,
            "total_power_export_kwh": 0.0,
            "total_power_export_t1_kwh": 0.0,
            "total_power_export_t2_kwh": 0.0,
            "active_power_w": 500.0,
        }
    )
    assert data.active_power_w == 500.0
    assert data.smr_version == 50


def test_measurement_from_v2_dict():
    data = Measurement.model_validate(
        {
            "protocol_version": 50,
            "meter_model": "TEST",
            "unique_id": "abc",
            "tariff": 1,
            "energy_import_kwh": 100.0,
            "energy_import_t1_kwh": 50.0,
            "energy_import_t2_kwh": 50.0,
            "energy_export_kwh": 0.0,
            "energy_export_t1_kwh": 0.0,
            "energy_export_t2_kwh": 0.0,
            "power_w": 500.0,
        }
    )
    assert data.active_power_w == 500.0
    assert data.total_power_import_kwh == 100.0
    assert data.smr_version == 50
