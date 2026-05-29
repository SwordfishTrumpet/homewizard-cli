import json
from pathlib import Path
from homewizard_cli.models import DataResponse, SystemResponse

FIXTURES = Path(__file__).parent / "fixtures"


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
    """Test that optional fields can be missing."""
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
