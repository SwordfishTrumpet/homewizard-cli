"""Tests for pure functions in export.py."""

import json
import os

from homewizard_cli.commands.export import (
    _filter_fields,
    _MetricsServer,
    _pid_is_alive,
    _resolve_export_option,
)
from homewizard_cli.models import DataResponse


def data() -> DataResponse:
    return DataResponse(
        wifi_ssid="Test",
        wifi_strength=100,
        smr_version=50,
        meter_model="ISKRA",
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
        active_power_l2_w=250.0,
    )


# ── _resolve_export_option ─────────────────────────────────────


def test_resolve_export_option_cli_wins():
    assert _resolve_export_option("json", "csv", "default") == "json"


def test_resolve_export_option_config_fallback():
    assert _resolve_export_option(None, "csv", "default") == "csv"


def test_resolve_export_option_default_fallback():
    assert _resolve_export_option(None, None, "default") == "default"


def test_resolve_export_option_none_default():
    assert _resolve_export_option(None, None) is None


def test_resolve_export_option_cli_overrides_config_even_when_config_set():
    assert _resolve_export_option("influx", "csv") == "influx"


# ── _filter_fields ─────────────────────────────────────────────


def test_filter_fields_returns_none_for_empty_string():
    assert _filter_fields(data(), "") is None
    assert _filter_fields(data(), None) is None


def test_filter_fields_single_field():
    result = _filter_fields(data(), "active_power_w")
    assert result == {"active_power_w": 500.0}


def test_filter_fields_multiple_fields():
    result = _filter_fields(data(), "active_power_w, total_power_import_kwh")
    assert result == {
        "active_power_w": 500.0,
        "total_power_import_kwh": 100.0,
    }


def test_filter_fields_handles_whitespace():
    result = _filter_fields(data(), "  active_power_w  ,  total_gas_m3  ")
    assert result == {
        "active_power_w": 500.0,
        "total_gas_m3": 7252.0,
    }


def test_filter_fields_includes_optional_fields():
    result = _filter_fields(data(), "active_power_l2_w")
    assert result == {"active_power_l2_w": 250.0}


def test_filter_fields_returns_json_serializable():
    result = _filter_fields(data(), "active_power_w,total_power_import_kwh")
    json.dumps(result)


# ── _pid_is_alive ──────────────────────────────────────────────


def test_pid_is_alive_current_process():
    assert _pid_is_alive(os.getpid()) is True


def test_pid_is_alive_nonexistent():
    # PID 99999 is unlikely to exist on any system, and killing with
    # signal 0 will raise ProcessLookupError (caught by OSError).
    assert _pid_is_alive(99999) is False


def test_pid_is_alive_negative():
    # Some systems treat negative PIDs differently.
    # We just verify it doesn't crash.
    result: bool = False
    try:
        result = _pid_is_alive(-1)
    except OSError:
        pass
    assert isinstance(result, bool)


# ── _MetricsServer._format_metrics ─────────────────────────────


def test_metrics_server_format_metrics_initial():
    ms = _MetricsServer()
    output = ms._format_metrics()
    assert "homewizard_readings_total 0" in output
    assert "homewizard_errors_total 0" in output
    assert "homewizard_last_poll_timestamp_seconds 0.0" in output


def test_metrics_server_format_metrics_after_usage():
    ms = _MetricsServer()
    ms.readings_total = 42
    ms.errors_total = 3
    ms.last_poll_timestamp = 1234567890.0
    output = ms._format_metrics()
    assert "homewizard_readings_total 42" in output
    assert "homewizard_errors_total 3" in output
    assert "homewizard_last_poll_timestamp_seconds 1234567890.0" in output


def test_metrics_server_format_metrics_has_help_and_type():
    ms = _MetricsServer()
    output = ms._format_metrics()
    assert "# HELP homewizard_readings_total" in output
    assert "# TYPE homewizard_readings_total counter" in output
    assert "# HELP homewizard_errors_total" in output
    assert "# TYPE homewizard_errors_total counter" in output
    assert "# HELP homewizard_last_poll_timestamp_seconds" in output
    assert "# TYPE homewizard_last_poll_timestamp_seconds gauge" in output


def test_metrics_server_format_metrics_prometheus_format():
    ms = _MetricsServer()
    ms.readings_total = 10
    ms.errors_total = 1
    ms.last_poll_timestamp = 1000000.0
    output = ms._format_metrics()
    # No extra whitespace in metric lines
    for line in output.split("\n"):
        if not line.startswith("#") and line != "":
            # Prometheus format: metric_name value
            parts = line.split()
            assert len(parts) == 2
            # value should be parseable as float
            float(parts[1])
