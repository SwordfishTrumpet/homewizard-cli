# tests/test_template.py
from rich.console import Console
from io import StringIO
from homewizard_cli.models import DataResponse
from homewizard_cli.format.template import write_template


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


def test_template_simple():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    write_template(data, console, "Power: {{.active_power_w}}W")
    result = output.getvalue()
    assert "Power: 500.0W" in result


def test_template_multiple_fields():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    write_template(
        data, console, "{{.active_power_w}}W | {{.total_power_import_kwh}}kWh"
    )
    result = output.getvalue()
    assert "500.0W | 100.0kWh" in result


def test_template_unknown_field():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    write_template(data, console, "{{.unknown}}")
    result = output.getvalue()
    assert result.strip() == ""


def test_template_no_placeholders():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = create_test_data()
    write_template(data, console, "static text")
    result = output.getvalue()
    assert "static text" in result


def test_template_optional_field_none():
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    data = DataResponse(
        wifi_ssid="Test",
        wifi_strength=50,
        smr_version=50,
        meter_model="M",
        unique_id="id",
        active_tariff=1,
        total_power_import_kwh=0.0,
        total_power_import_t1_kwh=0.0,
        total_power_import_t2_kwh=0.0,
        total_power_export_kwh=0.0,
        total_power_export_t1_kwh=0.0,
        total_power_export_t2_kwh=0.0,
        active_power_w=0.0,
    )
    write_template(data, console, "Gas: {{.total_gas_m3}}")
    result = output.getvalue()
    assert "Gas: " in result
