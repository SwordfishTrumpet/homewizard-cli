"""homewizard-cli quality command."""

import asyncio
import re

import typer
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..config import load_config, resolve_host
from ..models import Measurement
from ..util import format_p1_timestamp

app = typer.Typer()


def _type_name(logical_name: str) -> str:
    if logical_name == "0-0:96.7.19":
        return "Short outage"
    if logical_name == "0-0:96.7.9":
        return "Long outage"
    return "Unknown"


def _parse_events_from_telegram(raw: str) -> list[dict]:
    events: list[dict] = []
    obis_line = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("1-0:99.97.0"):
            obis_line = stripped
        elif obis_line is not None and stripped.startswith("("):
            obis_line += stripped

    if obis_line is None:
        events.append({"type": "normal", "timestamp": "", "duration": ""})
        return events

    parts = [p for p in re.findall(r"\(([^)]*)\)", obis_line) if p]
    if len(parts) < 2:
        events.append({"type": "normal", "timestamp": "", "duration": ""})
        return events

    try:
        count = int(parts[0])
    except ValueError:
        count = 0
    if count == 0:
        events.append({"type": "normal", "timestamp": "", "duration": ""})
        return events

    idx = 1
    current_type = None
    if "." in parts[idx]:
        current_type = parts[idx]
        idx += 1

    for _ in range(count):
        if idx >= len(parts):
            break
        if "." in parts[idx]:
            current_type = parts[idx]
            idx += 1
        if idx + 1 >= len(parts):
            break
        ts_raw = parts[idx]
        idx += 1
        duration_raw = parts[idx] if parts[idx].endswith("*s") else ""
        if duration_raw:
            idx += 1

        duration_s = duration_raw.replace("*s", "").lstrip("0")
        ts_str = ts_raw.rstrip("SW")
        try:
            ts_fmt = load_config().timestamp_format
            formatted_ts = format_p1_timestamp(ts_str, ts_fmt)
        except (ValueError, KeyError):
            formatted_ts = ts_str
        events.append(
            {
                "type": _type_name(current_type) if current_type else "Unknown",
                "timestamp": formatted_ts,
                "duration": duration_s,
            }
        )
    if not events:
        events.append({"type": "normal", "timestamp": "", "duration": ""})
    return events


@app.callback(invoke_without_command=True)
def quality(
    watch: float | None = typer.Option(None, "--watch", "-w", help="Poll interval"),
    alert: bool = typer.Option(False, "--alert", help="Only print when counts change"),
    events: bool = typer.Option(False, "--events", help="Show power failure event log"),
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
    """Display power quality information."""
    asyncio.run(
        _quality_async(
            watch,
            alert,
            events,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _quality_async(
    watch: float | None,
    alert: bool,
    show_events: bool,
    host: str | None,
    request_timeout: float,
    proxy: str | None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
):
    console = Console()
    host = resolve_host(host)
    if watch is not None and watch < 1.0:
        console.print(
            f"Warning: Polling interval {watch}s is below recommended minimum (1.0s).\n"
            "         Device may become unresponsive.",
            style="yellow",
        )
    previous = None
    client = resolve_client(
        api_version,
        host,
        request_timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )
    async with client as c:
        while True:
            if api_version == "v2":
                data = await c.get_json_v2("/api/measurement", Measurement)
            else:
                data = await c.get_json("/api/v1/data", Measurement)

            current = (
                data.voltage_sag_l1_count,
                data.voltage_swell_l1_count,
                data.voltage_sag_l2_count,
                data.voltage_swell_l2_count,
                data.voltage_sag_l3_count,
                data.voltage_swell_l3_count,
                data.any_power_fail_count,
                data.long_power_fail_count,
            )
            if alert and previous == current:
                if watch is None:
                    break
                await asyncio.sleep(watch)
                continue

            console.print(f"Voltage Sags L1: {data.voltage_sag_l1_count or 0}")
            console.print(f"Voltage Swells L1: {data.voltage_swell_l1_count or 0}")
            if data.voltage_sag_l2_count is not None:
                console.print(f"Voltage Sags L2: {data.voltage_sag_l2_count or 0}")
            if data.voltage_swell_l2_count is not None:
                console.print(f"Voltage Swells L2: {data.voltage_swell_l2_count or 0}")
            if data.voltage_sag_l3_count is not None:
                console.print(f"Voltage Sags L3: {data.voltage_sag_l3_count or 0}")
            if data.voltage_swell_l3_count is not None:
                console.print(f"Voltage Swells L3: {data.voltage_swell_l3_count or 0}")
            console.print(f"Short Failures:  {data.any_power_fail_count or 0}")
            console.print(f"Long Failures:   {data.long_power_fail_count or 0}")

            if show_events:
                try:
                    if api_version == "v2":
                        raw = await c.get("/api/telegram")
                    else:
                        raw = await c.get("/api/v1/telegram")
                    event_log = _parse_events_from_telegram(raw)
                    console.print("")
                    if event_log and event_log[0]["type"] == "normal":
                        console.print("Power Failure Events: None")
                    else:
                        console.print("Power Failure Events:")
                        for ev in event_log:
                            if ev["duration"]:
                                console.print(
                                    f"  {ev['timestamp']} \u2014 {ev['type']} "
                                    f"({ev['duration']} s)"
                                )
                            else:
                                console.print(
                                    f"  {ev['timestamp']} \u2014 {ev['type']}"
                                )
                except Exception as e:
                    console.print(f"  (could not fetch event log: {e})", style="yellow")

            previous = current

            if watch is None:
                break
            await asyncio.sleep(watch)
