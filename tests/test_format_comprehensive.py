"""Comprehensive tests for all output formatters."""

import json
from io import StringIO
from typing import Any
from unittest.mock import MagicMock

from rich.console import Console

from homewizard_cli.format import Format, write_data
from homewizard_cli.format.csv import write_csv
from homewizard_cli.format.env import write_env
from homewizard_cli.format.influx import write_influx
from homewizard_cli.format.json import write_json
from homewizard_cli.format.minimal import write_minimal
from homewizard_cli.format.mqtt import PersistentMqttClient
from homewizard_cli.format.prometheus import write_prometheus
from homewizard_cli.format.raw import write_raw
from homewizard_cli.format.table import write_table
from homewizard_cli.format.tsv import write_tsv
from homewizard_cli.models import DataResponse


def _console():
    return Console(file=StringIO(), force_terminal=False, width=9999)


def basic_data(**overrides: Any) -> DataResponse:
    defaults: dict[str, Any] = {
        "wifi_ssid": "TestNet",
        "wifi_strength": 80,
        "smr_version": 50,
        "meter_model": "ISKRA TEST",
        "unique_id": "abc123",
        "active_tariff": 1,
        "total_power_import_kwh": 100.0,
        "total_power_import_t1_kwh": 60.0,
        "total_power_import_t2_kwh": 40.0,
        "total_power_export_kwh": 0.0,
        "total_power_export_t1_kwh": 0.0,
        "total_power_export_t2_kwh": 0.0,
        "active_power_w": 500.0,
        "active_voltage_l1_v": 239.9,
        "total_gas_m3": 7252.0,
        "gas_unique_id": "gas123",
    }
    defaults.update(overrides)
    return DataResponse(**defaults)  # type: ignore[arg-type]


def full_3phase_data() -> DataResponse:
    return DataResponse(
        wifi_ssid="ThreePhase",
        wifi_strength=100,
        smr_version=50,
        meter_model="ISKRA 3PH",
        unique_id="dev123",
        active_tariff=2,
        total_power_import_kwh=10201.0,
        total_power_import_t1_kwh=5100.0,
        total_power_import_t2_kwh=5101.0,
        total_power_import_t3_kwh=0.0,
        total_power_import_t4_kwh=0.0,
        total_power_export_kwh=500.0,
        total_power_export_t1_kwh=250.0,
        total_power_export_t2_kwh=250.0,
        total_power_export_t3_kwh=0.0,
        total_power_export_t4_kwh=0.0,
        active_power_w=1500.0,
        active_power_l1_w=500.0,
        active_power_l2_w=600.0,
        active_power_l3_w=400.0,
        active_voltage_l1_v=230.0,
        active_voltage_l2_v=231.0,
        active_voltage_l3_v=229.0,
        active_current_l1_a=2.1,
        active_current_l2_a=2.6,
        active_current_l3_a=1.7,
        active_frequency_hz=50.0,
        active_power_average_w=1480.0,
        monthly_power_peak_w=3200.0,
        monthly_power_peak_timestamp=250529120000,
        voltage_sag_l1_count=1,
        voltage_sag_l2_count=2,
        voltage_sag_l3_count=0,
        voltage_swell_l1_count=0,
        voltage_swell_l2_count=1,
        voltage_swell_l3_count=0,
        any_power_fail_count=3,
        long_power_fail_count=1,
        total_gas_m3=7252.631,
        gas_timestamp=250529120000,
        gas_unique_id="gas123",
        text_message="test message",
    )


# ── InfluxDB ──────────────────────────────────────────────────


def test_influx_basic():
    c = _console()
    write_influx(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "p1_meter," in out
    assert "device=HWE-P1" in out
    assert "serial=abc123" in out
    assert "active_power_w=500.0" in out
    assert "total_power_import_kwh=100.0" in out
    assert "total_power_export_kwh=0.0" in out
    assert "total_gas_m3=7252.0" in out
    assert "active_voltage_l1_v=239.9" in out


def test_influx_3phase():
    c = _console()
    write_influx(full_3phase_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "active_power_l2_w=600.0" in out
    assert "active_power_l3_w=400.0" in out
    assert "active_voltage_l3_v=229.0" in out
    assert "active_frequency_hz=50.0" in out


def test_influx_meter_model_spaces_replaced():
    c = _console()
    write_influx(basic_data(meter_model="ISKRA 2M550E-1011"), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "meter_model=ISKRA_2M550E-1011" in out


def test_influx_optional_fields_omitted():
    c = _console()
    write_influx(basic_data(total_gas_m3=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "total_gas_m3" not in out
    assert "active_power_l2_w" not in out


def test_influx_timestamp_nanoseconds():
    c = _console()
    write_influx(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    # timestamp is last field: should be a large integer (nanoseconds)
    parts = out.strip().split()
    assert len(parts) == 3
    ts = int(parts[2])
    assert ts > 1_700_000_000_000_000_000  # reasonable epoch ns


# ── Prometheus ────────────────────────────────────────────────


def test_prometheus_basic():
    c = _console()
    write_prometheus(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "p1_active_power_w 500.0" in out
    assert "p1_total_power_import_kwh 100.0" in out
    assert "p1_total_power_export_kwh 0.0" in out
    assert "# HELP" in out
    assert "# TYPE" in out


def test_prometheus_with_gas():
    c = _console()
    write_prometheus(basic_data(total_gas_m3=1234.5), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "p1_total_gas_m3 1234.5" in out
    assert "# HELP p1_total_gas_m3" in out
    assert "# TYPE p1_total_gas_m3 counter" in out


def test_prometheus_3phase():
    c = _console()
    write_prometheus(full_3phase_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "p1_active_power_l2_w 600.0" in out
    assert "p1_active_power_l3_w 400.0" in out
    assert "p1_active_voltage_l2_v 231.0" in out
    assert "p1_active_voltage_l3_v 229.0" in out
    assert "p1_active_frequency_hz 50.0" in out
    assert "p1_total_gas_m3 7252.631" in out


def test_prometheus_no_optional_fields():
    c = _console()
    minimal = basic_data()
    minimal.active_voltage_l1_v = None
    minimal.total_gas_m3 = None
    write_prometheus(minimal, c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "p1_active_power_w 500.0" in out
    assert "p1_total_power_import_kwh 100.0" in out
    assert "p1_total_power_export_kwh 0.0" in out
    assert "gas_m3" not in out
    assert "voltage_l1" not in out
    assert "voltage_l2" not in out
    assert "voltage_l3" not in out


# ── CSV ────────────────────────────────────────────────────────


def test_csv_header():
    c = _console()
    write_csv(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    lines = out.strip().split("\n")
    assert len(lines) == 2
    header = lines[0]
    assert "timestamp" in header
    assert "active_power_w" in header
    assert "total_power_import_kwh" in header
    assert "total_gas_m3" in header


def test_csv_values():
    c = _console()
    write_csv(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    lines = out.strip().split("\n")
    values = lines[1].split(",")
    assert values[1] == "500.0"
    assert values[8] == "100.0"  # import
    assert values[9] == "0.0"  # export
    assert values[10] == "7252.0"  # gas


def test_csv_optional_fields_empty():
    c = _console()
    write_csv(basic_data(active_voltage_l1_v=None, total_gas_m3=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    lines = out.strip().split("\n")
    values = lines[1].split(",")
    assert values[3] == ""  # L1 voltage
    assert values[10] == ""  # gas


def test_csv_3phase():
    c = _console()
    write_csv(full_3phase_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    lines = out.strip().split("\n")
    values = lines[1].split(",")
    assert "600.0" in values[2]  # L2 power
    assert "400.0" in values[3]  # L3 power


# ── TSV ────────────────────────────────────────────────────────


def test_tsv_header():
    c = _console()
    write_tsv(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    lines = out.split("\n")
    assert len(lines) >= 2
    assert "\t" in out
    assert "active_power_w" in lines[0]


def test_tsv_values():
    c = _console()
    write_tsv(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    lines = out.split("\n")
    values = lines[1].split("\t")
    assert values[1] == "500.0"


def test_tsv_optional_fields_empty():
    c = _console()
    write_tsv(basic_data(active_voltage_l1_v=None, total_gas_m3=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    lines = out.split("\n")
    values = lines[1].split("\t")
    assert values[3] == ""
    assert values[10] == ""


# ── ENV (Shell Export) ─────────────────────────────────────────


def test_env_basic():
    c = _console()
    write_env(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "export P1_ACTIVE_POWER_W=500.0" in out
    assert "export P1_TOTAL_POWER_IMPORT_KWH=100.0" in out
    assert "export P1_TOTAL_POWER_EXPORT_KWH=0.0" in out
    assert "export P1_TOTAL_GAS_M3=7252.0" in out
    assert "export P1_METER_MODEL='ISKRA TEST'" in out
    assert "export P1_SERIAL='abc123'" in out


def test_env_none_fields_skipped():
    c = _console()
    write_env(
        basic_data(active_voltage_l1_v=None, active_power_l2_w=None, total_gas_m3=None),
        c,
    )
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "P1_ACTIVE_VOLTAGE_L1_V" not in out
    assert "P1_ACTIVE_POWER_L2_W" not in out
    assert "P1_TOTAL_GAS_M3" not in out


def test_env_all_optional_present():
    c = _console()
    write_env(full_3phase_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "P1_ACTIVE_POWER_L2_W" in out
    assert "P1_ACTIVE_POWER_L3_W" in out
    assert "P1_ACTIVE_VOLTAGE_L1_V" in out
    assert "P1_ACTIVE_VOLTAGE_L2_V" in out
    assert "P1_ACTIVE_VOLTAGE_L3_V" in out
    assert "P1_ACTIVE_FREQUENCY_HZ" in out


# ── JSON ───────────────────────────────────────────────────────


def test_json_contains_model_fields():
    c = _console()
    write_json(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    parsed = json.loads(out)
    assert parsed["wifi_ssid"] == "TestNet"
    assert parsed["active_power_w"] == 500.0
    assert parsed["total_gas_m3"] == 7252.0


def test_json_non_nullable_fields():
    c = _console()
    write_json(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    parsed = json.loads(out)
    assert parsed["smr_version"] == 50
    assert parsed["active_tariff"] == 1


# ── Minimal ────────────────────────────────────────────────────


def test_minimal_basic():
    c = _console()
    write_minimal(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "500.0 W" in out
    assert "239.9 V" in out
    assert "100.0 kWh in" in out
    assert "0.0 kWh out" in out
    assert "7252.0 m\u00b3 gas" in out


def test_minimal_no_voltage():
    c = _console()
    write_minimal(basic_data(active_voltage_l1_v=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert " V" not in out


def test_minimal_no_gas():
    c = _console()
    write_minimal(basic_data(total_gas_m3=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "gas" not in out


# ── Raw (DSMR reconstruction) ──────────────────────────────────


def test_raw_basic():
    c = _console()
    write_raw(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "/ISKRA TEST" in out
    assert "1-0:1.8.1" in out  # import T1
    assert "1-0:2.8.1" in out  # export T1
    assert "!" in out
    # CRC appended after "!" on last line
    lines = out.strip().split("\n")
    last = lines[-1]
    assert last.startswith("!")
    assert len(last) == 5  # "!" + 4 hex chars


def test_raw_3phase():
    c = _console()
    write_raw(full_3phase_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "1-0:21.7.0" in out  # L1 power delivered
    assert "1-0:41.7.0" in out  # L2 power delivered
    assert "1-0:61.7.0" in out  # L3 power delivered
    assert "1-0:32.7.0" in out  # L1 voltage
    assert "1-0:52.7.0" in out  # L2 voltage
    assert "1-0:72.7.0" in out  # L3 voltage
    assert "1-0:31.7.0" in out  # L1 current
    assert "1-0:51.7.0" in out  # L2 current
    assert "1-0:71.7.0" in out  # L3 current
    assert "1-0:14.7.0" in out  # frequency
    assert "1-0:15.7.0" in out  # average power
    assert "1-0:16.7.0" in out  # monthly peak
    assert "0-0:96.13.0" in out  # text message


def test_raw_negative_power_uses_export_obis():
    c = _console()
    write_raw(basic_data(active_power_w=-500.0), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "1-0:2.7.0" in out  # export for negative
    assert "1-0:1.7.0" not in out  # not import


def test_raw_quality_counts():
    c = _console()
    write_raw(full_3phase_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "1-0:32.32.0" in out  # sag L1
    assert "1-0:52.32.0" in out  # sag L2
    assert "1-0:72.32.0" in out  # sag L3
    assert "1-0:32.36.0" in out  # swell L1
    assert "1-0:52.36.0" in out  # swell L2
    assert "1-0:72.36.0" in out  # swell L3
    assert "0-0:96.7.21" in out  # any power fail
    assert "0-0:96.7.9" in out  # long power fail


def test_raw_gas_detail():
    c = _console()
    write_raw(basic_data(total_gas_m3=1234.567, gas_unique_id="gas123"), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "0-1:24.1.0(003)" in out
    assert "0-1:96.1.0(gas123)" in out
    assert "0-1:24.2.1" in out


def test_raw_no_gas():
    c = _console()
    write_raw(basic_data(total_gas_m3=None, gas_unique_id=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "0-1:" not in out


def test_raw_tariff_t2():
    c = _console()
    write_raw(basic_data(active_tariff=2), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "0-0:96.14.0(0002)" in out


def test_raw_t3_t4_tariffs():
    c = _console()
    write_raw(
        basic_data(
            total_power_import_t3_kwh=10.0,
            total_power_import_t4_kwh=5.0,
            total_power_export_t3_kwh=1.0,
            total_power_export_t4_kwh=0.5,
        ),
        c,
    )
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "1-0:1.8.3" in out
    assert "1-0:1.8.4" in out
    assert "1-0:2.8.3" in out
    assert "1-0:2.8.4" in out


# ── Table ──────────────────────────────────────────────────────


def test_table_basic():
    c = _console()
    write_table(basic_data(), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "P1 Meter" in out
    assert "ISKRA TEST" in out
    assert "500.0 W" in out
    assert "239.9 V" in out
    assert "100.0 kWh" in out
    assert "TestNet" in out


def test_table_gas():
    c = _console()
    write_table(basic_data(total_gas_m3=1234.5), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "1234.5 m" in out  # m³


def test_table_no_gas():
    c = _console()
    write_table(basic_data(total_gas_m3=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "Gas" not in out


# ── write_data dispatcher ──────────────────────────────────────


def test_write_data_dispatches_to_correct_formatter():
    data = basic_data()

    c = _console()
    write_data(data, Format.JSON, c)
    assert "wifi_ssid" in c.file.getvalue()  # type: ignore[union-attr]

    c = _console()
    write_data(data, Format.CSV, c)
    assert "active_power_w" in c.file.getvalue()  # type: ignore[union-attr]

    c = _console()
    write_data(data, Format.PROMETHEUS, c)
    assert "p1_active_power_w" in c.file.getvalue()  # type: ignore[union-attr]

    c = _console()
    write_data(data, Format.INFLUX, c)
    assert "p1_meter" in c.file.getvalue()  # type: ignore[union-attr]

    c = _console()
    write_data(data, Format.ENV, c)
    assert "export P1_" in c.file.getvalue()  # type: ignore[union-attr]

    c = _console()
    write_data(data, Format.MINIMAL, c)
    assert "500.0 W" in c.file.getvalue()  # type: ignore[union-attr]

    c = _console()
    write_data(data, Format.RAW, c)
    assert "/ISKRA" in c.file.getvalue()  # type: ignore[union-attr]

    c = _console()
    write_data(data, Format.TSV, c)
    assert "\t" in c.file.getvalue()  # type: ignore[union-attr]


def test_write_data_auto_fallsback_to_json_when_not_tty():
    c = _console()
    write_data(basic_data(), Format.AUTO, c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "wifi_ssid" in out  # JSON in pipe mode


# ── Table edge cases ───────────────────────────────────────────


def test_table_with_none_voltage():
    """Test write_table with active_voltage_l1_v=None does not crash."""
    c = _console()
    write_table(basic_data(active_voltage_l1_v=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "P1 Meter" in out
    assert "Voltage" not in out


def test_table_with_none_current():
    """Test write_table with active_current_l1_a=None does not crash."""
    c = _console()
    write_table(basic_data(active_current_l1_a=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "Current" not in out


def test_table_with_none_gas():
    """Test write_table with total_gas_m3=None omits gas row."""
    c = _console()
    write_table(basic_data(total_gas_m3=None, gas_timestamp=None), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "Gas" not in out
    assert "Gas Time" not in out


def test_table_with_none_wifi():
    """Test write_table with wifi_ssid empty string still renders."""
    c = _console()
    write_table(basic_data(wifi_ssid="", wifi_strength=0), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "WiFi" in out


def test_table_with_all_none_optional_fields():
    """Test write_table with all optional fields set to None."""
    c = _console()
    write_table(
        basic_data(
            active_voltage_l1_v=None,
            active_current_l1_a=None,
            total_gas_m3=None,
            gas_timestamp=None,
            gas_unique_id=None,
        ),
        c,
    )
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "P1 Meter" in out
    assert "WiFi" in out
    assert "DSMR" in out
    assert "Tariff" in out
    assert "Power" in out
    assert "Import Total" in out
    assert "Export Total" in out
    assert "Voltage" not in out
    assert "Current" not in out
    assert "Gas" not in out


# ── MQTT edge cases ───────────────────────────────────────────


def test_mqtt_buffer_overflow_drops_oldest():
    """Test PersistentMqttClient buffer drops oldest messages when full."""
    from unittest.mock import patch

    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.publish.side_effect = OSError("fail")
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t", max_buffer=3)
        client._client = mock_client

        import asyncio

        d1 = basic_data(active_power_w=1.0)
        d2 = basic_data(active_power_w=2.0)
        d3 = basic_data(active_power_w=3.0)
        d4 = basic_data(active_power_w=4.0)

        asyncio.run(client.publish(d1))
        asyncio.run(client.publish(d2))
        asyncio.run(client.publish(d3))
        assert client.pending == 3

        asyncio.run(client.publish(d4))
        assert client.pending == 3  # oldest (d1) dropped

        # When we finally succeed, the buffer should drain the remaining 3
        mock_client.publish.side_effect = None
        result = asyncio.run(client.publish(d4))
        assert result is True
        assert client.pending == 0


def test_mqtt_drain_failure_requeues():
    """Test drain failure re-queues the buffered message at the front."""
    from unittest.mock import patch

    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        call_count = [0]

        def publish_side_effect(topic, payload, qos=0):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("fail")
            if call_count[0] == 2:
                # First drain attempt fails
                raise OSError("drain fail")
            return None

        mock_client = MagicMock()
        mock_client.publish.side_effect = publish_side_effect
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        d1 = basic_data(active_power_w=1.0)
        d2 = basic_data(active_power_w=2.0)

        # First publish fails, buffer = [d1]
        result1 = asyncio.run(client.publish(d1))
        assert result1 is False
        assert client.pending == 1

        # Second publish succeeds, drain fails, requeues d1
        result2 = asyncio.run(client.publish(d2))
        assert result2 is False
        assert client.pending == 2


def test_mqtt_drain_failure_then_success():
    """Test that a failed drain eventually succeeds on retry."""
    from unittest.mock import patch

    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        call_count = [0]

        def publish_side_effect(topic, payload, qos=0):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("fail")
            if call_count[0] == 2:
                raise OSError("drain fail")
            return None

        mock_client = MagicMock()
        mock_client.publish.side_effect = publish_side_effect
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        d1 = basic_data(active_power_w=1.0)
        d2 = basic_data(active_power_w=2.0)
        d3 = basic_data(active_power_w=3.0)

        # First publish fails, buffer = [d1]
        result1 = asyncio.run(client.publish(d1))
        assert result1 is False
        assert client.pending == 1

        # Second publish succeeds, drain fails, buffer = [d1, d2]
        result2 = asyncio.run(client.publish(d2))
        assert result2 is False
        assert client.pending == 2

        # Third publish succeeds, drains d1 and d2
        result3 = asyncio.run(client.publish(d3))
        assert result3 is True
        assert client.pending == 0


def test_raw_no_gas_with_gas_unique_id():
    """Raw output: total_gas_m3=None, gas_unique_id set still omits gas lines."""
    c = _console()
    write_raw(basic_data(total_gas_m3=None, gas_unique_id="gas123"), c)
    out = c.file.getvalue()  # type: ignore[union-attr]
    assert "0-1:" not in out


def test_mqtt_publish_success_with_empty_buffer():
    """Test publish succeeds when buffer is empty and no new failures."""
    from unittest.mock import patch

    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        result = asyncio.run(client.publish(basic_data()))
        assert result is True
        assert client.pending == 0
        mock_client.publish.assert_called_once()
