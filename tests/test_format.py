import pytest
from rich.console import Console
from io import StringIO
from homewizard_cli.models import DataResponse
from homewizard_cli.format import Format, write_data, get_format
from homewizard_cli.format.json import write_json
from homewizard_cli.format.table import write_table
from homewizard_cli.format.minimal import write_minimal


def create_test_data():
    return DataResponse(
        wifi_ssid="Test",
        wifi_strength=100,
        smr_version=50,
        meter_model="ISKRA TEST",
        unique_id="abc",
        active_tariff=1,
        total_power_import_kwh=100.0,
        total_power_import_t1_kwh=50.0,
        total_power_import_t2_kwh=50.0,
        total_power_export_kwh=0.0,
        total_power_export_t1_kwh=0.0,
        total_power_export_t2_kwh=0.0,
        active_power_w=500.0,
        active_voltage_l1_v=239.9,
        total_gas_m3=7252.0,
    )


def test_get_format_auto_tty():
    assert get_format("auto", is_tty=True) == Format.TABLE


def test_get_format_auto_pipe():
    assert get_format("auto", is_tty=False) == Format.JSON


def test_get_format_explicit():
    assert get_format("json") == Format.JSON
    assert get_format("table") == Format.TABLE
    assert get_format("minimal") == Format.MINIMAL


def test_write_json():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    write_json(data, console)
    result = output.getvalue()
    assert "wifi_ssid" in result
    assert "Test" in result


def test_write_table():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    write_table(data, console)
    result = output.getvalue()
    assert "P1 Meter" in result
    assert "ISKRA TEST" in result
    assert "500.0 W" in result


def test_write_minimal():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    write_minimal(data, console)
    result = output.getvalue()
    assert "500.0 W" in result
    assert "239.9 V" in result
    assert "100.0 kWh in" in result


def test_write_csv():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    from homewizard_cli.format.csv import write_csv

    write_csv(data, console)
    result = output.getvalue()
    assert "active_power_w" in result


def test_write_tsv():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    from homewizard_cli.format.tsv import write_tsv

    write_tsv(data, console)
    result = output.getvalue()
    assert "active_power_w" in result


def test_write_influx():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    from homewizard_cli.format.influx import write_influx

    write_influx(data, console)
    result = output.getvalue()
    assert "p1_meter" in result
    assert "active_power_w=500.0" in result


def test_write_prometheus():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    from homewizard_cli.format.prometheus import write_prometheus

    write_prometheus(data, console)
    result = output.getvalue()
    assert "p1_active_power_w" in result
    assert "500.0" in result


def test_write_env():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    from homewizard_cli.format.env import write_env

    write_env(data, console)
    result = output.getvalue()
    assert "P1_ACTIVE_POWER_W" in result
    assert "P1_METER_MODEL" in result


def test_write_raw():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    from homewizard_cli.format.raw import write_raw

    write_raw(data, console)
    result = output.getvalue()
    assert "ISKRA TEST" in result
    assert "*kWh" in result


def test_get_format_explicit_all():
    for fmt in [
        "json",
        "table",
        "csv",
        "tsv",
        "influx",
        "prometheus",
        "env",
        "minimal",
        "raw",
    ]:
        assert get_format(fmt) == Format(fmt)
