"""Tests for homewizard_cli/commands/data.py complex paths."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from homewizard_cli.commands.data import _data_async
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


# ── Template output ────────────────────────────────────────────


def test_data_template():
    client = _make_client_mock(
        _make_measurement(active_power_w=500.0, total_power_import_kwh=100.0)
    )
    with patch("homewizard_cli.commands.data.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "data",
                "--template",
                "{{.active_power_w}}W {{.total_power_import_kwh}}kWh",
            ],
        )
    assert result.exit_code == 0
    assert "500.0W 100.0kWh" in result.output


# ── Fields output ──────────────────────────────────────────────


def test_data_fields_table():
    client = _make_client_mock(
        _make_measurement(active_power_w=500.0, active_voltage_l1_v=239.9)
    )
    with patch("homewizard_cli.commands.data.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "data",
                "--fields",
                "active_power_w,active_voltage_l1_v",
                "--format",
                "table",
            ],
        )
    assert result.exit_code == 0
    assert "active_power_w" in result.output
    assert "500.0" in result.output
    assert "239.9" in result.output


def test_data_fields_json():
    client = _make_client_mock(_make_measurement(active_power_w=500.0))
    with patch("homewizard_cli.commands.data.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "data",
                "--fields",
                "active_power_w",
                "--format",
                "json",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["active_power_w"] == 500.0


# ── Query JSONPath ─────────────────────────────────────────────


def test_data_query_jsonpath():
    client = _make_client_mock(_make_measurement(active_power_w=500.0))
    with patch("homewizard_cli.commands.data.resolve_client", return_value=client):
        result = runner.invoke(app, ["data", "--query", "$.active_power_w"])
    assert result.exit_code == 0
    assert "500.0" in result.output


# ── Delta watch mode ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_data_delta_watch():
    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_measurement(active_power_w=500.0)
        elif call_count == 2:
            return _make_measurement(active_power_w=600.0)
        else:
            raise RuntimeError("stop")

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.data.resolve_client", return_value=client),
        patch("homewizard_cli.commands.data.asyncio.sleep", side_effect=mock_sleep),
        pytest.raises(RuntimeError, match="stop"),
    ):
        await _data_async(
            watch=1.0,
            fields=None,
            format="auto",
            host="192.168.1.1",
            request_timeout=3.0,
            delta=True,
        )

    assert call_count >= 2
    assert sleep_calls >= 2


# ── WebSocket tests ────────────────────────────────────────────


def test_data_ws_oneshot():
    with patch("homewizard_cli.commands.data.WebSocketClient") as mock_ws_class:
        ws_instance = AsyncMock()
        ws_instance.__aenter__ = AsyncMock(return_value=ws_instance)
        ws_instance.__aexit__ = AsyncMock(return_value=False)
        ws_instance.receive_data = AsyncMock(
            return_value={
                "active_power_w": 500.0,
                "total_power_import_kwh": 100.0,
            }
        )
        mock_ws_class.return_value = ws_instance

        result = runner.invoke(app, ["data", "--ws"])
        assert result.exit_code == 0
        assert "500.0" in result.output
        mock_ws_class.assert_called_once()


def test_data_ws_watch():
    with patch("homewizard_cli.commands.data.WebSocketClient") as mock_ws_class:
        ws_instance = AsyncMock()
        ws_instance.__aenter__ = AsyncMock(return_value=ws_instance)
        ws_instance.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        async def mock_receive():
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                return None
            return {
                "active_power_w": 500.0 + call_count * 400,
                "total_power_import_kwh": 100.0,
            }

        ws_instance.receive_data = AsyncMock(side_effect=mock_receive)
        mock_ws_class.return_value = ws_instance

        result = runner.invoke(
            app,
            [
                "data",
                "--ws",
                "--watch",
                "1.0",
                "--until",
                "active_power_w > 1000",
            ],
        )
        assert result.exit_code == 10
        assert "Condition met" in result.output
        assert call_count >= 2


# ── Alert webhook tests ────────────────────────────────────────


def test_data_alert_webhook_until():
    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = mock_post
    mock_post.return_value = mock_response

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch(
            "homewizard_cli.commands.data.resolve_client",
            return_value=_make_client_mock(_make_measurement(active_power_w=1500.0)),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "data",
                "--until",
                "active_power_w > 1000",
                "--alert-webhook",
                "https://hooks.example.com/test",
            ],
        )
        assert result.exit_code == 10
        assert "Condition met" in result.output
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.example.com/test"
        payload = call_args[1]["json"]
        assert payload["condition"] == "active_power_w > 1000"
        assert payload["data"]["active_power_w"] == 1500.0


# ── Agg watch mode ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_data_agg_watch():
    call_count = 0

    async def side_effect(endpoint, model):
        nonlocal call_count
        call_count += 1
        return _make_measurement(active_power_w=500.0 + call_count * 100)

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=side_effect)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.data.resolve_client", return_value=client),
        patch("homewizard_cli.commands.data.asyncio.sleep", side_effect=mock_sleep),
        pytest.raises(RuntimeError, match="stop"),
    ):
        await _data_async(
            watch=1.0,
            fields=None,
            format="auto",
            host="192.168.1.1",
            request_timeout=3.0,
            agg=True,
        )

    assert call_count >= 3
    assert sleep_calls >= 3


# ── Query bare field name ──────────────────────────────────────


def test_data_query_bare_field():
    client = _make_client_mock(_make_measurement(active_power_w=500.0))
    with patch("homewizard_cli.commands.data.resolve_client", return_value=client):
        result = runner.invoke(app, ["data", "--query", "active_power_w"])
    assert result.exit_code == 0
    assert "500.0" in result.output


def test_data_query_boolean_expression():
    client = _make_client_mock(_make_measurement(active_power_w=500.0))
    with patch("homewizard_cli.commands.data.resolve_client", return_value=client):
        result = runner.invoke(app, ["data", "--query", "active_power_w > 100"])
    assert result.exit_code == 0
    assert "true" in result.output.lower()
