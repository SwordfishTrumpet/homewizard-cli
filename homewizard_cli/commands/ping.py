"""homewizard-cli ping command — ICMP echo check."""

import re
import subprocess  # nosec: B404

import typer
from rich.console import Console

from ..config import resolve_host

app = typer.Typer()

_TIME_RE = re.compile(r"time=([0-9.]+)\s*ms")


@app.callback(invoke_without_command=True)
def ping(
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only exit code, no output"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: int = typer.Option(3, "--timeout", "-t", help="Ping timeout (seconds)"),
):
    """Check if the P1 meter is reachable via ICMP."""
    host = resolve_host(host)
    console = Console()
    try:
        result = subprocess.run(  # nosec
            ["ping", "-c", "1", "-W", str(timeout), host],
            capture_output=True,
            text=True,
            timeout=timeout + 2,
        )
        if result.returncode == 0:
            m = _TIME_RE.search(result.stdout)
            elapsed = m.group(1) if m else "?"
            if not quiet:
                console.print(f"P1 Meter at {host} \u2014 OK ({elapsed}ms)")
        else:
            if not quiet:
                console.print(f"P1 Meter at {host} \u2014 FAIL", style="red")
            raise typer.Exit(code=2) from None
    except subprocess.TimeoutExpired:
        if not quiet:
            console.print(f"P1 Meter at {host} — FAIL (timeout)", style="red")
        raise typer.Exit(code=2) from None
