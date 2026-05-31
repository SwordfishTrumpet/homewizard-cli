"""Property-based tests using hypothesis for homewizard-cli models and utilities."""

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from homewizard_cli.models import Measurement
from homewizard_cli.models.measurement import _iso_to_compact_timestamp
from homewizard_cli.models.v2 import DeviceInfoV2, MeasurementV2, SystemV2, TelegramV2

# ── Measurement model ──────────────────────────────────────────


@given(
    st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=300, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
)
def test_measurement_roundtrip(power, import_kwh, export_kwh, voltage, current):
    data = {
        "active_power_w": power,
        "total_power_import_kwh": import_kwh,
        "total_power_export_kwh": export_kwh,
        "active_voltage_l1_v": voltage,
        "active_current_l1_a": current,
    }
    m = Measurement(**data)
    dumped = m.model_dump()
    assert dumped["active_power_w"] == power
    assert dumped["total_power_import_kwh"] == import_kwh
    assert dumped["total_power_export_kwh"] == export_kwh


@given(
    st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False)
)
def test_measurement_power_roundtrip(power):
    m = Measurement(active_power_w=power)
    assert m.active_power_w == power


@given(st.text())
def test_measurement_wifi_ssid_roundtrip(ssid):
    m = Measurement(wifi_ssid=ssid)
    assert m.wifi_ssid == ssid


# ── v2 field mapping ────────────────────────────────────────────


@given(
    st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_v2_to_v1_mapping(power, energy):
    v2_data = {
        "power_w": power,
        "energy_import_kwh": energy,
    }
    m = Measurement.model_validate(v2_data)
    assert m.active_power_w == power
    assert m.total_power_import_kwh == energy


@given(
    st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_v2_to_v1_all_fields(power, import_kwh, export_kwh):
    v2_data = {
        "power_w": power,
        "energy_import_kwh": import_kwh,
        "energy_export_kwh": export_kwh,
    }
    m = Measurement.model_validate(v2_data)
    assert m.active_power_w == power
    assert m.total_power_import_kwh == import_kwh
    assert m.total_power_export_kwh == export_kwh


@given(st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_v2_total_gas_mapping(gas_m3):
    """total_gas_m3 maps directly (same name in v1 and v2)."""
    m = Measurement.model_validate({"total_gas_m3": gas_m3})
    assert m.total_gas_m3 == gas_m3


@given(st.integers(min_value=0, max_value=999999999999))
def test_v2_timestamp_mapping(ts):
    v2_data = {
        "power_w": 100,
        "total_power_import_kwh": 50,
        "gas_timestamp": str(ts),
    }
    m = Measurement.model_validate(v2_data)
    assert m.active_power_w == 100.0


# ── Timestamp conversion ───────────────────────────────────────


@given(
    st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31),
    )
)
def test_iso_to_compact_timestamp(dt):
    iso = dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    result = _iso_to_compact_timestamp(iso)
    assert isinstance(result, int)
    assert len(str(result)) == 12
    reconstructed = datetime.strptime(str(result), "%y%m%d%H%M%S")
    assert reconstructed.year == dt.year
    assert reconstructed.month == dt.month
    assert reconstructed.day == dt.day


@given(st.text())
def test_iso_to_compact_timestamp_invalid(text):
    result = _iso_to_compact_timestamp(text)
    assert result is None


# ── MeasurementV2 model ────────────────────────────────────────


@given(
    st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False)
)
def test_measurement_v2_power(power):
    m = MeasurementV2(power_w=power)
    assert m.power_w == power


@given(st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_measurement_v2_energy(energy):
    m = MeasurementV2(energy_import_kwh=energy)
    assert m.energy_import_kwh == energy


@given(st.floats(min_value=0, max_value=300, allow_nan=False, allow_infinity=False))
def test_measurement_v2_voltage(voltage):
    m = MeasurementV2(voltage_l1_v=voltage)
    assert m.voltage_l1_v == voltage


@given(st.text(), st.text(), st.text())
def test_device_info_v2(product_type, serial, product_name):
    d = DeviceInfoV2(
        product_type=product_type, serial=serial, product_name=product_name
    )
    assert d.product_type == product_type
    assert d.serial == serial
    assert d.product_name == product_name


@given(st.booleans())
def test_system_v2_cloud(cloud):
    s = SystemV2(cloud_enabled=cloud)
    assert s.cloud_enabled == cloud


@given(st.text(max_size=100))
def test_telegram_v2_text(text):
    t = TelegramV2(telegram=text)
    assert t.telegram == text
