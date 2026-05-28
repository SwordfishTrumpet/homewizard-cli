"""homewizard-cli telegram command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..obis import lookup_obis

app = typer.Typer()


@app.callback(invoke_without_command=True)
def telegram(
    validate: bool = typer.Option(False, "--validate", help="Validate CRC"),
    obis: Optional[str] = typer.Option(
        None, "--obis", help="Extract specific OBIS code"
    ),
    watch: Optional[float] = typer.Option(None, "--watch", "-w", help="Poll interval"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    explain: Optional[str] = typer.Option(
        None, "--explain", help="Explain an OBIS code"
    ),
):
    """Access raw DSMR telegram from the P1 meter."""
    asyncio.run(_telegram_async(validate, obis, explain, watch, host, timeout))


async def _telegram_async(validate, obis, explain, watch, host, timeout):
    console = Console()

    if explain:
        desc = lookup_obis(explain)
        if desc:
            console.print(f"{explain} — {desc}")
        else:
            console.print(f"Unknown OBIS code: {explain}", style="yellow")
        return

    async with P1Client(host, timeout) as client:
        while True:
            try:
                raw = await client.get("/api/v1/telegram")
            except Exception as e:
                console.print(f"Error fetching telegram: {e}", style="red")
                if watch is None:
                    raise
                await asyncio.sleep(watch)
                continue

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
            else:
                console.print(raw.strip())

            if watch is None:
                break
            await asyncio.sleep(watch)


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
            console.print(f"CRC: {received_crc} — Valid", style="green")
        else:
            console.print(
                f"CRC: received {received_crc}, computed {computed_hex} — Invalid",
                style="red",
            )
    else:
        console.print("No CRC found in telegram", style="yellow")
    console.print(stripped)


def _crc16(data: bytes) -> int:
    """Compute CRC16-IBM (CRC-16/ARC) checksum."""
    crc = 0x0000
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc
