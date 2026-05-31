"""Tests for MQTT output formatter."""

import json
from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console

from homewizard_cli.format.mqtt import (
    PersistentMqttClient,
    _parse_broker_url,
    write_mqtt,
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
    )


def _console():
    return Console(file=StringIO(), force_terminal=False, width=9999)


# ── _parse_broker_url ──────────────────────────────────────────


def test_parse_broker_url_host_and_port():
    host, port = _parse_broker_url("192.168.1.1:1883")
    assert host == "192.168.1.1"
    assert port == 1883


def test_parse_broker_url_host_only_defaults_port():
    host, port = _parse_broker_url("192.168.1.1")
    assert host == "192.168.1.1"
    assert port == 1883


def test_parse_broker_url_mqtt_prefix_stripped():
    host, port = _parse_broker_url("mqtt://192.168.1.1:1883")
    assert host == "192.168.1.1"
    assert port == 1883


def test_parse_broker_url_hostname_without_port():
    host, port = _parse_broker_url("mqtt.example.com")
    assert host == "mqtt.example.com"
    assert port == 1883


def test_parse_broker_url_non_numeric_port_defaults():
    host, port = _parse_broker_url("host:abc")
    # When port parsing fails, the function returns the original broker string
    # as host with the default port
    assert port == 1883


def test_parse_broker_url_empty_returns_default():
    host, port = _parse_broker_url("")
    assert host == ""
    assert port == 1883


# ── write_mqtt ─────────────────────────────────────────────────


def test_write_mqtt_prints_payload_even_on_connect_failure():
    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.connect.side_effect = OSError("Connection refused")
        mock_client_cls.return_value = mock_client

        c = _console()
        write_mqtt(data(), c, broker="localhost:1883", topic="test/topic")

        out = c.file.getvalue()  # type: ignore[union-attr]
        assert "MQTT error" in out


def test_write_mqtt_success_prints_payload():
    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        c = _console()
        write_mqtt(data(), c, broker="localhost:1883", topic="test/topic")

        out = c.file.getvalue()  # type: ignore[union-attr]
        # payload is multi-line pretty JSON, parse all lines
        payload = json.loads(out.strip())
        assert payload["active_power_w"] == 500.0
        assert payload["meter_model"] == "ISKRA"

        mock_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
        mock_client.publish.assert_called_once()
        args = mock_client.publish.call_args
        assert args[0][0] == "test/topic"
        assert json.loads(args[0][1])["active_power_w"] == 500.0


# ── PersistentMqttClient ───────────────────────────────────────


def test_persistent_mqtt_client_init():
    client = PersistentMqttClient(broker="host:1883", topic="test/topic", qos=1)
    assert client.broker == "host:1883"
    assert client.topic == "test/topic"
    assert client.qos == 1
    assert client.host == "host"
    assert client.port == 1883
    assert client.pending == 0


def test_persistent_mqtt_client_default_qos():
    client = PersistentMqttClient(broker="host:1883", topic="t")
    assert client.qos == 0


def test_persistent_mqtt_client_custom_max_buffer():
    client = PersistentMqttClient(broker="host:1883", topic="t", max_buffer=50)
    assert client._buffer.maxlen == 50


def test_persistent_mqtt_client_close_disconnects():
    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        asyncio.run(client.close())

        mock_client.disconnect.assert_called_once()


def test_persistent_mqtt_client_close_handles_oserror():
    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.disconnect.side_effect = OSError
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        asyncio.run(client.close())  # should not raise


def test_persistent_mqtt_client_publish_returns_true_on_success():
    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        result = asyncio.run(client.publish(data()))
        assert result is True
        mock_client.publish.assert_called_once()


def test_persistent_mqtt_client_publish_returns_false_on_oserror():
    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.publish.side_effect = OSError
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        result = asyncio.run(client.publish(data()))
        assert result is False
        assert client.pending == 1


def test_persistent_mqtt_client_buffers_on_failure_then_drains():
    with patch("homewizard_cli.format.mqtt.mqtt.Client") as mock_client_cls:
        call_count = [0]

        def publish_side_effect(topic, payload, qos=0):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("fail")
            # subsequent calls succeed
            return None

        mock_client = MagicMock()
        mock_client.publish.side_effect = publish_side_effect
        mock_client_cls.return_value = mock_client

        client = PersistentMqttClient(broker="host:1883", topic="t")
        client._client = mock_client

        import asyncio

        # First publish fails, queues to buffer
        result1 = asyncio.run(client.publish(data()))
        assert result1 is False
        assert client.pending == 1

        # Second publish succeeds, drains buffer
        result2 = asyncio.run(client.publish(data()))
        assert result2 is True
        assert client.pending == 0
        # 1 failed + 1 drained + 1 new = 3 calls
        assert mock_client.publish.call_count == 3
