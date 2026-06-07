"""homewizard-cli hass command — Home Assistant discovery configuration."""

import asyncio

import typer

from ..util import _dumps_json, _loads_json
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..config import resolve_host
from ..models import Measurement
from ..models.v2 import DeviceInfoV2, SystemV2

app = typer.Typer()

_MQTT_SENSORS = (
    ("Power", "power", "measurement", "W", "mdi:lightning-bolt"),
    (
        "Energy Import",
        "energy",
        "total_increasing",
        "kWh",
        "mdi:transmission-tower-import",
    ),
    (
        "Energy Export",
        "energy",
        "total_increasing",
        "kWh",
        "mdi:transmission-tower-export",
    ),
    ("Gas", "gas", "total_increasing", "m\u00b3", "mdi:gas-cylinder"),
    ("Water", "water", "total_increasing", "m\u00b3", "mdi:water"),
    ("Voltage L1", "voltage", "measurement", "V", "mdi:flash"),
    ("Current L1", "current", "measurement", "A", "mdi:current-ac"),
)

_SENSOR_FIELD = {
    "Power": "active_power_w",
    "Energy Import": "total_power_import_kwh",
    "Energy Export": "total_power_export_kwh",
    "Gas": "total_gas_m3",
    "Water": "total_water_m3",
    "Voltage L1": "active_voltage_l1_v",
    "Current L1": "active_current_l1_a",
}


@app.callback(invoke_without_command=True)
def hass(
    mqtt: bool = typer.Option(False, "--mqtt", help="Output MQTT discovery topics"),
    rest: bool = typer.Option(False, "--rest", help="Output REST configuration.yaml"),
    topic_prefix: str = typer.Option(
        "homewizard", "--topic-prefix", help="MQTT state topic prefix"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
):
    """Generate Home Assistant discovery configuration."""
    asyncio.run(
        _hass_async(
            mqtt,
            rest,
            topic_prefix,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _hass_async(
    mqtt: bool,
    rest: bool,
    topic_prefix: str,
    host: str | None,
    request_timeout: float,
    proxy: str | None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
):
    console = Console()
    host = resolve_host(host)
    client = resolve_client(
        api_version,
        host,
        request_timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )

    async with client as c:
        if api_version == "v2":
            device = await c.get_json_v2("/api", DeviceInfoV2)
            await c.get_json_v2("/api/measurement", Measurement)
            await c.get_json_v2("/api/system", SystemV2)
        else:
            raw = await c.get("/api/")
            device = DeviceInfoV2(**_loads_json(raw))

    serial = device.serial or "unknown"
    device_cfg = {
        "identifiers": [serial],
        "name": device.product_name or "P1 Meter",
        "model": device.product_type or "HWE-P1",
        "manufacturer": "HomeWizard",
    }

    use_mqtt = mqtt or not rest

    if use_mqtt:
        for name, device_class, state_class, unit, icon in _MQTT_SENSORS:
            field = _SENSOR_FIELD[name]
            payload = {
                "name": f"{device_cfg['name']} {name}",
                "state_topic": f"{topic_prefix}/{serial}/state",
                "value_template": f"{{{{ value_json.{field} }}}}",
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": state_class,
                "icon": icon,
                "unique_id": f"{serial}_{field}",
                "device": device_cfg,
            }
            topic = f"homeassistant/sensor/{serial}/{field}/config"
            console.print(_dumps_json({"topic": topic, "payload": payload}, indent=True))
    else:
        sensors = []
        _protocol = "https" if api_version == "v2" else "http"
        _endpoint = "/api/measurement" if api_version == "v2" else "/api/v1/data"
        for name, device_class, state_class, unit, icon in _MQTT_SENSORS:
            field = _SENSOR_FIELD[name]
            sensors.append(
                {
                    "platform": "rest",
                    "name": name,
                    "device_class": device_class,
                    "state_class": state_class,
                    "unit_of_measurement": unit,
                    "icon": icon,
                    "value_template": f"{{{{ value_json.{field} }}}}",
                    "resource": f"{_protocol}://{host}{_endpoint}",
                    "device": device_cfg,
                }
            )
        console.print(_dumps_json({"sensor": sensors}, indent=True))
