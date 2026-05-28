"""homewizard-cli telegram command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client

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
):
    """Access raw DSMR telegram from the P1 meter."""
    asyncio.run(_telegram_async(validate, obis, watch, host, timeout))


async def _telegram_async(validate, obis, watch, host, timeout):
    console = Console()
    async with P1Client(host, timeout) as client:
        while True:
            raw = await client.get("/api/v1/telegram")

            if obis:
                for line in raw.splitlines():
                    if line.startswith(obis):
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
    lines = raw.strip().splitlines()
    if not lines:
        console.print("Empty telegram", style="red")
        return
    last_line = lines[-1].strip()
    if last_line.startswith("!"):
        received_crc = last_line[1:]
        crc_line = raw.strip().rsplit("!", 1)[0]
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
    console.print(raw.strip())


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
