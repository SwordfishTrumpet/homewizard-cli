"""MQTT output formatter."""

import asyncio
import json
from collections import deque

import paho.mqtt.client as mqtt
from rich.console import Console
from homewizard_cli.models import DataResponse


def _parse_broker_url(broker: str) -> tuple[str, int]:
    if broker.startswith("mqtt://"):
        broker = broker[7:]
    if ":" in broker:
        host, port_str = broker.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            return broker, 1883
        return host, port
    return broker, 1883


def write_mqtt(
    data: DataResponse,
    console: Console,
    broker: str,
    topic: str,
    qos: int = 0,
):
    payload = json.dumps(data.model_dump(), indent=2, default=str)
    host, port = _parse_broker_url(broker)

    client = mqtt.Client()
    try:
        client.connect(host, port, keepalive=60)
        client.loop(timeout=0.1)
        client.publish(topic, payload, qos=qos)
        client.loop(timeout=1.0)
    except OSError as e:
        console.print(f"MQTT error: {e}", style="red")
        return
    finally:
        try:
            client.disconnect()
        except OSError:
            pass

    console.print(payload)


class PersistentMqttClient:
    """Persistent async MQTT client that reuses connections across polls."""

    def __init__(self, broker: str, topic: str, qos: int = 0, max_buffer: int = 100):
        self.broker = broker
        self.topic = topic
        self.qos = qos
        self.host: str
        self.port: int
        self.host, self.port = _parse_broker_url(broker)
        self._client: mqtt.Client | None = None
        self._buffer: deque[str] = deque(maxlen=max_buffer)
        self._backoff = 1.0
        self._max_backoff = 60.0

    def _connect(self) -> None:
        if self._client is None:
            self._client = mqtt.Client()
        self._client.connect(self.host, self.port, keepalive=60)
        self._client.loop(timeout=0.1)

    def _disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except OSError:
                pass
            self._client = None

    def _publish_sync(self, payload: str) -> bool:
        try:
            if self._client is None:
                self._connect()
            assert self._client is not None
            self._client.publish(self.topic, payload, qos=self.qos)
            self._client.loop(timeout=1.0)
            self._backoff = 1.0
            return True
        except OSError:
            self._disconnect()
            return False

    async def publish(self, data: DataResponse) -> bool:
        payload = json.dumps(data.model_dump(), indent=2, default=str)
        success = await asyncio.to_thread(self._publish_sync, payload)
        if not success:
            self._buffer.append(payload)
            return False
        # Drain buffered messages
        while self._buffer:
            buffered = self._buffer.popleft()
            ok = await asyncio.to_thread(self._publish_sync, buffered)
            if not ok:
                self._buffer.appendleft(buffered)
                return False
        return True

    async def close(self) -> None:
        await asyncio.to_thread(self._disconnect)

    @property
    def pending(self) -> int:
        return len(self._buffer)
