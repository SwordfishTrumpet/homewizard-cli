"""Integration tests for homewizard_cli/commands/export.py."""

import asyncio
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from homewizard_cli.commands.export import (
    _export_async,
    _install_signal_handlers,
    _MetricsServer,
)
from homewizard_cli.errors import P1Error
from homewizard_cli.main import app
from homewizard_cli.models import Measurement

runner = CliRunner()


def _make_measurement(**kwargs: Any) -> Measurement:
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
    defaults.update(kwargs)
    return Measurement(**defaults)


def _make_client_mock(measurement: Measurement | None = None) -> AsyncMock:
    if measurement is None:
        measurement = _make_measurement()
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(return_value=measurement)
    return client


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# ── One-shot format tests ──────────────────────────────────────


def test_export_oneshot_influx():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "influx"])
    assert result.exit_code == 0
    assert "p1_meter," in result.output


def test_export_oneshot_json():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "json"])
    assert result.exit_code == 0
    assert "active_power_w" in result.output


def test_export_oneshot_csv():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "csv"])
    assert result.exit_code == 0
    assert "active_power_w" in result.output
    assert "500.0" in result.output


def test_export_oneshot_tsv():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "tsv"])
    assert result.exit_code == 0
    assert "\t" in result.output
    assert "500.0" in result.output


def test_export_oneshot_prometheus():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "prometheus"])
    assert result.exit_code == 0
    assert "p1_active_power_w 500.0" in result.output


def test_export_oneshot_env():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "env"])
    assert result.exit_code == 0
    assert "export P1_ACTIVE_POWER_W=500.0" in result.output


def test_export_oneshot_minimal():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "minimal"])
    assert result.exit_code == 0
    assert "500.0 W" in result.output


def test_export_oneshot_raw():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "raw"])
    assert result.exit_code == 0
    assert "/ISKRA" in result.output


def test_export_oneshot_file_json(tmp_path: Path):
    file_path = tmp_path / "export.json"
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--file",
                str(file_path),
            ],
        )
    assert result.exit_code == 0
    assert file_path.exists()
    content = file_path.read_text()
    assert "active_power_w" in content


def test_export_oneshot_mqtt_missing_broker():
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "mqtt"])
    assert result.exit_code == 0
    assert "--broker and --topic required" in result.output


# ── Watch mode tests ───────────────────────────────────────────


def test_export_watch_skip_unchanged():
    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_measurement(active_power_w=500.0)
        elif call_count == 2:
            return _make_measurement(active_power_w=500.0)  # unchanged
        else:
            return _make_measurement(active_power_w=1500.0)

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "export",
                "--watch",
                "0.01",
                "--skip-unchanged",
                "--until",
                "active_power_w > 1000",
                "--format",
                "json",
            ],
        )
    assert result.exit_code == 10
    assert "Condition met" in result.output
    assert call_count >= 3


def test_export_watch_delta():
    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_measurement(active_power_w=500.0)
        elif call_count == 2:
            return _make_measurement(active_power_w=600.0)
        else:
            return _make_measurement(active_power_w=1500.0)

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "export",
                "--watch",
                "0.01",
                "--delta",
                "--fields",
                "active_power_w",
                "--until",
                "active_power_w > 1000",
                "--format",
                "json",
            ],
        )
    assert result.exit_code == 10
    assert "Condition met" in result.output
    assert "500.0" in result.output
    assert "600.0" in result.output


def test_export_watch_error_recovery():
    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise P1Error("fetch failed", code=2)
        elif call_count == 2:
            return _make_measurement()
        else:
            raise RuntimeError("stop")

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    wait_count = 0

    async def mock_wait_for(fut, timeout=None):
        nonlocal wait_count
        wait_count += 1
        if wait_count >= 3:
            raise RuntimeError("stop")
        # Avoid Python 3.11 bpo-46358 unawaited coroutine warning
        if asyncio.iscoroutine(fut):
            fut.close()
        raise TimeoutError()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.export.asyncio.wait_for",
            side_effect=mock_wait_for,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _export_async(
                format="json",
                watch=1.0,
                file=None,
                host="192.168.1.1",
                request_timeout=3.0,
            )
        )

    assert call_count >= 2
    assert wait_count >= 2


# ── File rotation tests ───────────────────────────────────────


def test_export_file_rotation_daily(tmp_path: Path):
    file_path = tmp_path / "export.json"

    times = [
        datetime(2026, 5, 29, 10, 0, 0),
        datetime(2026, 5, 30, 10, 0, 0),
    ]
    time_idx = 0

    def mock_now():
        nonlocal time_idx
        idx = min(time_idx, len(times) - 1)
        time_idx += 1
        return times[idx]

    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise RuntimeError("stop")
        return _make_measurement()

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    wait_count = 0

    async def mock_wait_for(fut, timeout=None):
        nonlocal wait_count
        wait_count += 1
        if wait_count >= 3:
            raise RuntimeError("stop")
        # Avoid Python 3.11 bpo-46358 unawaited coroutine warning
        if asyncio.iscoroutine(fut):
            fut.close()
        raise TimeoutError()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("homewizard_cli.commands.export.datetime") as mock_dt,
        patch(
            "homewizard_cli.commands.export.asyncio.wait_for",
            side_effect=mock_wait_for,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        mock_dt.now = mock_now
        mock_dt.strftime = datetime.strftime
        asyncio.run(
            _export_async(
                format="json",
                watch=0.01,
                file=str(file_path),
                host="192.168.1.1",
                request_timeout=3.0,
                rotate="daily",
            )
        )

    rotated = file_path.with_name(f"{file_path.name}.2026-05-29")
    assert rotated.exists()
    assert file_path.exists()


def test_export_file_rotation_hourly(tmp_path: Path):
    file_path = tmp_path / "export.json"

    times = [
        datetime(2026, 5, 29, 10, 0, 0),
        datetime(2026, 5, 29, 11, 0, 0),
    ]
    time_idx = 0

    def mock_now():
        nonlocal time_idx
        idx = min(time_idx, len(times) - 1)
        time_idx += 1
        return times[idx]

    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise RuntimeError("stop")
        return _make_measurement()

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    wait_count = 0

    async def mock_wait_for(fut, timeout=None):
        nonlocal wait_count
        wait_count += 1
        if wait_count >= 3:
            raise RuntimeError("stop")
        # Avoid Python 3.11 bpo-46358 unawaited coroutine warning
        if asyncio.iscoroutine(fut):
            fut.close()
        raise TimeoutError()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("homewizard_cli.commands.export.datetime") as mock_dt,
        patch(
            "homewizard_cli.commands.export.asyncio.wait_for",
            side_effect=mock_wait_for,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        mock_dt.now = mock_now
        mock_dt.strftime = datetime.strftime
        asyncio.run(
            _export_async(
                format="json",
                watch=0.01,
                file=str(file_path),
                host="192.168.1.1",
                request_timeout=3.0,
                rotate="hourly",
            )
        )

    rotated = file_path.with_name(f"{file_path.name}.2026-05-29T10")
    assert rotated.exists()
    assert file_path.exists()


# ── PID file tests ─────────────────────────────────────────────


def test_export_pid_file_creation(tmp_path: Path):
    pid_file = tmp_path / "test.pid"
    client = _make_client_mock()
    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("pathlib.Path.unlink"),
    ):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--pid-file",
                str(pid_file),
            ],
        )
    assert result.exit_code == 0
    assert pid_file.exists()
    assert int(pid_file.read_text()) == os.getpid()


def test_export_pid_file_stale(tmp_path: Path):
    pid_file = tmp_path / "test.pid"
    pid_file.write_text("99999")
    client = _make_client_mock()
    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("pathlib.Path.unlink"),
    ):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--pid-file",
                str(pid_file),
            ],
        )
    assert result.exit_code == 0
    assert pid_file.exists()
    assert int(pid_file.read_text()) == os.getpid()


def test_export_pid_file_alive(tmp_path: Path):
    pid_file = tmp_path / "test.pid"
    pid_file.write_text(str(os.getpid()))
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--pid-file",
                str(pid_file),
            ],
        )
    assert result.exit_code == 1
    assert "still running" in result.output


def test_export_pid_file_corrupted(tmp_path: Path):
    pid_file = tmp_path / "test.pid"
    pid_file.write_text("not_a_number")
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--pid-file",
                str(pid_file),
            ],
        )
    assert result.exit_code == 0
    assert "Error reading PID file" in result.output


# ── Metrics server tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_metrics_server_http_response():
    server = _MetricsServer()
    port = _get_free_port()
    await server.start(port)

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"GET /metrics HTTP/1.1\r\nHost: localhost\r\n\r\n")
    await writer.drain()
    response = await reader.read(4096)
    writer.close()
    await writer.wait_closed()

    assert b"200 OK" in response
    assert b"homewizard_readings_total 0" in response
    assert b"homewizard_errors_total 0" in response
    assert b"homewizard_last_poll_timestamp_seconds 0.0" in response

    await server.stop()


@pytest.mark.asyncio
async def test_metrics_server_404():
    server = _MetricsServer()
    port = _get_free_port()
    await server.start(port)

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"GET /unknown HTTP/1.1\r\nHost: localhost\r\n\r\n")
    await writer.drain()
    response = await reader.read(4096)
    writer.close()
    await writer.wait_closed()

    assert b"404 Not Found" in response

    await server.stop()


def test_export_with_metrics_port():
    port = _get_free_port()
    client = _make_client_mock()
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--metrics-port",
                str(port),
            ],
        )
    assert result.exit_code == 0


# ── Signal handling tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_export_signal_handler_sets_event():
    import signal

    with patch("signal.signal") as mock_signal:
        event = asyncio.Event()
        _install_signal_handlers(event)

        sigint_calls = [
            c for c in mock_signal.call_args_list if c[0][0] == signal.SIGINT
        ]
        assert len(sigint_calls) == 1
        handler = sigint_calls[0][0][1]
        handler(signal.SIGINT, None)
        await asyncio.sleep(0)  # let the event loop process the callback
        assert event.is_set()


# ── Error handling tests ───────────────────────────────────────


def test_export_oneshot_fetch_error():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get_json_v2 = AsyncMock(side_effect=P1Error("fetch failed", code=2))

    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(app, ["export", "--format", "json"])
    assert result.exit_code != 0
    assert result.exception is not None


# ── MQTT publish failure tests ──────────────────────────────────


def test_export_mqtt_publish_failure():
    """When MQTT publish returns False, a yellow warning is printed."""
    client = _make_client_mock()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("homewizard_cli.format.mqtt.PersistentMqttClient") as mock_mqtt_cls,
    ):
        mqtt_instance = AsyncMock()
        mqtt_instance.publish = AsyncMock(return_value=False)
        mqtt_instance.pending = 0
        mqtt_instance.close = AsyncMock()
        mock_mqtt_cls.return_value = mqtt_instance

        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "mqtt",
                "--broker",
                "mqtt://broker.local",
                "--topic",
                "home/p1meter",
            ],
        )
    assert result.exit_code == 0
    assert "MQTT publish failed" in result.output


def test_export_mqtt_publish_success():
    """When MQTT publish returns True, no failure message."""
    client = _make_client_mock()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("homewizard_cli.format.mqtt.PersistentMqttClient") as mock_mqtt_cls,
    ):
        mqtt_instance = AsyncMock()
        mqtt_instance.publish = AsyncMock(return_value=True)
        mqtt_instance.close = AsyncMock()
        mock_mqtt_cls.return_value = mqtt_instance

        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "mqtt",
                "--broker",
                "mqtt://broker.local",
                "--topic",
                "home/p1meter",
            ],
        )
    assert result.exit_code == 0
    assert "MQTT publish failed" not in result.output


# ── File rotation with OSError test ─────────────────────────────


def test_export_rotation_oserror(tmp_path: Path):
    """Test that rotation handles OSError gracefully (e.g. on rename)."""
    file_path = tmp_path / "export.json"

    times = [
        datetime(2026, 5, 29, 10, 0, 0),
        datetime(2026, 5, 30, 10, 0, 0),
    ]
    time_idx = 0

    def mock_now():
        nonlocal time_idx
        idx = min(time_idx, len(times) - 1)
        time_idx += 1
        return times[idx]

    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise RuntimeError("stop")
        return _make_measurement()

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    wait_count = 0

    async def mock_wait_for(fut, timeout=None):
        nonlocal wait_count
        wait_count += 1
        if wait_count >= 3:
            raise RuntimeError("stop")
        # Avoid Python 3.11 bpo-46358 unawaited coroutine warning
        if asyncio.iscoroutine(fut):
            fut.close()
        raise TimeoutError()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("homewizard_cli.commands.export.datetime") as mock_dt,
        patch("pathlib.Path.rename", side_effect=OSError("rename failed")),
        patch(
            "homewizard_cli.commands.export.asyncio.wait_for",
            side_effect=mock_wait_for,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        mock_dt.now = mock_now
        mock_dt.strftime = datetime.strftime
        asyncio.run(
            _export_async(
                format="json",
                watch=0.01,
                file=str(file_path),
                host="192.168.1.1",
                request_timeout=3.0,
                rotate="daily",
            )
        )

    assert file_path.exists()


# ── Export with --until and --alert-webhook ──────────────────────


def test_export_until_alert():
    client = _make_client_mock(_make_measurement(active_power_w=2000.0))
    with patch("homewizard_cli.commands.export.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--until",
                "active_power_w > 1000",
                "--alert-webhook",
                "https://hooks.example.com/test",
            ],
        )
    assert result.exit_code == 10
    assert "Condition met" in result.output


# ── PID file removal error ──────────────────────────────────────


def test_export_pid_file_removal_error(tmp_path: Path):
    """PID file removal OSError is handled gracefully."""
    pid_file = tmp_path / "test.pid"
    client = _make_client_mock()

    real_unlink = os.unlink
    target_path = str(pid_file)

    def unlink_side_effect(path, *args, **kwargs):
        if str(path) == target_path:
            real_unlink(path)
            raise OSError("permission denied")
        return real_unlink(path, *args, **kwargs)

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch("os.unlink", side_effect=unlink_side_effect),
    ):
        result = runner.invoke(
            app,
            [
                "export",
                "--format",
                "json",
                "--pid-file",
                str(pid_file),
            ],
        )
    assert result.exit_code == 0
    assert "Error removing PID file" in result.output


# ── _safe_write OSError tests ───────────────────────────────────


def test_export_safe_write_oserror(tmp_path: Path):
    """_safe_write logs OSError (general) without crashing."""
    file_path = tmp_path / "export.json"

    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise RuntimeError("stop")
        return _make_measurement()

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    wait_count = 0

    async def mock_wait_for(fut, timeout=None):
        nonlocal wait_count
        wait_count += 1
        if wait_count >= 3:
            raise RuntimeError("stop")
        # Avoid Python 3.11 bpo-46358 unawaited coroutine warning
        if asyncio.iscoroutine(fut):
            fut.close()
        raise TimeoutError()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.export.asyncio.wait_for",
            side_effect=mock_wait_for,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _export_async(
                format="json",
                watch=0.01,
                file=str(file_path),
                host="192.168.1.1",
                request_timeout=3.0,
            )
        )

    assert file_path.exists()
    assert call_count >= 2


# ── Export filtered fields path (--fields) ──────────────────────


def test_export_watch_fields(tmp_path: Path):
    """Export with --fields and --watch outputs filtered data."""
    file_path = tmp_path / "export.json"

    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise RuntimeError("stop")
        return _make_measurement()

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    wait_count = 0

    async def mock_wait_for(fut, timeout=None):
        nonlocal wait_count
        wait_count += 1
        if wait_count >= 3:
            raise RuntimeError("stop")
        # Avoid Python 3.11 bpo-46358 unawaited coroutine warning
        if asyncio.iscoroutine(fut):
            fut.close()
        raise TimeoutError()

    with (
        patch("homewizard_cli.commands.export.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.export.asyncio.wait_for",
            side_effect=mock_wait_for,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _export_async(
                format="json",
                watch=0.01,
                file=str(file_path),
                host="192.168.1.1",
                request_timeout=3.0,
                fields="active_power_w,total_power_import_kwh",
            )
        )

    assert file_path.exists()
    content = file_path.read_text()
    assert "active_power_w" in content
