"""Snapshot tests for all output formatters using syrupy."""

from io import StringIO
from typing import Any

from rich.console import Console

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


# ── Snapshot tests: basic data ─────────────────────────────────


def test_snapshot_json_basic(snapshot):
    from homewizard_cli.format.json import write_json

    c = _console()
    write_json(basic_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


def test_snapshot_prometheus_basic(snapshot):
    from homewizard_cli.format.prometheus import write_prometheus

    c = _console()
    write_prometheus(basic_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


def test_snapshot_env_basic(snapshot):
    from homewizard_cli.format.env import write_env

    c = _console()
    write_env(basic_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


def test_snapshot_minimal_basic(snapshot):
    from homewizard_cli.format.minimal import write_minimal

    c = _console()
    write_minimal(basic_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


def test_snapshot_raw_basic(snapshot):
    from homewizard_cli.format.raw import write_raw

    c = _console()
    write_raw(basic_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


def test_snapshot_table_basic(snapshot):
    from homewizard_cli.format.table import write_table

    c = _console()
    write_table(basic_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


# ── Snapshot tests: 3-phase data ──────────────────────────────


def test_snapshot_json_3phase(snapshot):
    from homewizard_cli.format.json import write_json

    c = _console()
    write_json(full_3phase_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


def test_snapshot_prometheus_3phase(snapshot):
    from homewizard_cli.format.prometheus import write_prometheus

    c = _console()
    write_prometheus(full_3phase_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]


def test_snapshot_raw_3phase(snapshot):
    from homewizard_cli.format.raw import write_raw

    c = _console()
    write_raw(full_3phase_data(), c)
    assert c.file.getvalue() == snapshot


def test_snapshot_table_no_gas(snapshot):
    from homewizard_cli.format.table import write_table

    c = _console()
    write_table(basic_data(total_gas_m3=None), c)
    assert c.file.getvalue() == snapshot


def test_snapshot_json_no_gas(snapshot):
    from homewizard_cli.format.json import write_json

    c = _console()
    write_json(basic_data(total_gas_m3=None), c)
    assert c.file.getvalue() == snapshot


def test_snapshot_raw_tariff_t2(snapshot):
    from homewizard_cli.format.raw import write_raw

    c = _console()
    write_raw(basic_data(active_tariff=2), c)
    assert c.file.getvalue() == snapshot


def test_snapshot_env_all_optional_present(snapshot):
    from homewizard_cli.format.env import write_env

    c = _console()
    write_env(full_3phase_data(), c)
    assert c.file.getvalue() == snapshot  # type: ignore[union-attr]
