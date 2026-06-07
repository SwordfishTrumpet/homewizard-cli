"""homewizard-cli telegram command."""

import asyncio
import json
import time
from collections import deque

import typer
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..config import resolve_host
from ..obis import lookup_obis
from ..util import _crc16

app = typer.Typer()


@app.callback(invoke_without_command=True)
def telegram(
    validate: bool = typer.Option(False, "--validate", help="Validate CRC"),
    obis: str | None = typer.Option(None, "--obis", help="Extract specific OBIS code"),
    watch: float | None = typer.Option(None, "--watch", "-w", help="Poll interval"),
    format: str = typer.Option("auto", "--format", "-f", help="Output format"),
    rate: bool = typer.Option(False, "--rate", help="Count telegrams per minute"),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    explain: str | None = typer.Option(None, "--explain", help="Explain an OBIS code"),
    named: bool = typer.Option(
        False, "--named", help="Use human-readable OBIS names in JSON output"
    ),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
):
    """Access raw DSMR telegram from the P1 meter."""
    asyncio.run(
        _telegram_async(
            validate,
            obis,
            explain,
            named,
            watch,
            format,
            rate,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _telegram_async(
    validate: bool,
    obis: str | None,
    explain: str | None,
    named: bool,
    watch: float | None,
    format: str,
    rate: bool,
    host: str | None,
    request_timeout: float,
    proxy: str | None = None,
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

    if explain:
        desc = lookup_obis(explain)
        if desc:
            console.print(f"{explain} \u2014 {desc}")
        else:
            console.print(f"Unknown OBIS code: {explain}", style="yellow")
        return

    output_json = format == "json"
    rate_timestamps: deque[float] = deque()

    client = resolve_client(
        api_version,
        host,
        request_timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )
    endpoint = "/api/telegram" if api_version == "v2" else "/api/v1/telegram"

    async with client as c:
        while True:
            try:
                raw = await c.get(endpoint)
            except Exception as e:
                console.print(f"Error fetching telegram: {e}", style="red")
                if watch is None:
                    raise
                await asyncio.sleep(watch)
                continue

            if rate:
                now = time.monotonic()
                rate_timestamps.append(now)
                cutoff = now - 60.0
                while rate_timestamps and rate_timestamps[0] < cutoff:
                    rate_timestamps.popleft()
                elapsed = now - (rate_timestamps[0] if rate_timestamps else now)
                rate_per_min = (
                    len(rate_timestamps) / max(elapsed, 0.1) * 60
                    if len(rate_timestamps) > 1
                    else 0.0
                )

            if obis:
                for line in raw.splitlines():
                    if line.split("(")[0] == obis:
                        console.print(line)
                        if watch is None:
                            return
                        break
                else:
                    console.print(f"OBIS code {obis} not found")
                    if watch is None:
                        return
            elif validate:
                _validate_and_print(raw, console)
            elif output_json:
                parsed = _parse_telegram(raw)
                if named:
                    parsed["obis"] = {
                        lookup_obis(k) or k: v for k, v in parsed["obis"].items()
                    }
                output = json.dumps(parsed, indent=2, default=str)
                if rate:
                    output += f"\nRate: {rate_per_min:.1f} telegrams/minute"
                console.print(output)
            elif rate:
                console.print(f"Rate: {rate_per_min:.1f} telegrams/minute")
            else:
                console.print(raw.strip())

            if watch is None:
                break
            await asyncio.sleep(watch)


def _parse_telegram(raw: str) -> dict:
    lines = raw.strip().splitlines()
    parsed: dict = {
        "header": "",
        "timestamp": "",
        "obis": {},
        "crc": "",
        "valid": False,
    }

    obis_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("/"):
            parsed["header"] = stripped
        elif stripped.startswith("!"):
            parsed["crc"] = stripped[1:]
        else:
            obis_lines.append(stripped)

    for line in obis_lines:
        if "(" in line:
            code, rest = line.split("(", 1)
            value = rest.rstrip(")")
            parsed["obis"][code] = value
            if code == "0-0:1.0.0":
                parsed["timestamp"] = value

    if parsed["crc"]:
        crc_line = raw.strip().rsplit("!", 1)[0]
        computed = _crc16(crc_line.encode("ascii"))
        parsed["valid"] = parsed["crc"].upper() == f"{computed:04X}"

    return parsed


def _validate_and_print(raw: str, console: Console):
    """Validate telegram CRC and print result."""
    stripped = raw.strip()
    lines = stripped.splitlines()
    if not lines:
        console.print("Empty telegram", style="red")
        return
    last_line = lines[-1].strip()
    if last_line.startswith("!"):
        received_crc = last_line[1:]
        crc_line = stripped.rsplit("!", 1)[0]
        computed = _crc16(crc_line.encode("ascii"))
        computed_hex = f"{computed:04X}"
        valid = received_crc.upper() == computed_hex.upper()
        if valid:
            console.print(f"CRC: {received_crc} \u2014 Valid", style="green")
        else:
            console.print(
                f"CRC: received {received_crc}, computed {computed_hex} \u2014 Invalid",
                style="red",
            )
    else:
        console.print("No CRC found in telegram", style="yellow")
    console.print(stripped)
