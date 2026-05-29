"""homewizard-cli data command."""

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

from ..alerting import AlertDispatcher
from ..client_factory import resolve_client, convert_v2_measurement, API_VERSIONS
from ..models import DataResponse
from ..models.v2 import MeasurementV2
from ..format import write_data, get_format, Format
from ..expr import evaluate_until
from ..jsonpath import query_jsonpath
from ..state import DeltaTracker
from ..config import resolve_host
from ..ws_client import WebSocketClient


def _filter_fields(data: DataResponse, fields_str: str | None) -> dict | None:
    if not fields_str:
        return None
    wanted = set(f.strip() for f in fields_str.split(","))
    return {k: v for k, v in data.model_dump().items() if k in wanted}


app = typer.Typer()


@app.callback(invoke_without_command=True)
def data(
    watch: float | None = typer.Option(
        None, "--watch", "-w", help="Poll interval in seconds (idle timeout in WS mode)"
    ),
    fields: str | None = typer.Option(
        None, "--fields", help="Comma-separated field list"
    ),
    format: str = typer.Option("auto", "--format", "-f", help="Output format"),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    until: str | None = typer.Option(
        None, "--until", help="Exit when expression is true"
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        help="Custom output template (e.g. '{{.active_power_w}}W')",
    ),
    delta: bool = typer.Option(
        False, "--delta", help="Show only changed fields (requires --watch)"
    ),
    query: str | None = typer.Option(
        None, "--query", "-q", help="JSONPath expression to filter data"
    ),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
    ws: bool = typer.Option(
        False,
        "--ws",
        help="Use WebSocket for real-time push (v2 only, requires websockets)",
    ),
    alert_webhook: str | None = typer.Option(
        None,
        "--alert-webhook",
        help="Webhook URL to POST when --until condition fires",
    ),
    alert_cmd: str | None = typer.Option(
        None,
        "--alert-cmd",
        help="Shell command to run when --until condition fires",
    ),
    alert_cooldown: float = typer.Option(
        0.0,
        "--alert-cooldown",
        help="Minimum seconds between alert dispatches",
    ),
):
    """Fetch and display full energy data."""
    asyncio.run(
        _data_async(
            watch,
            fields,
            format,
            host,
            request_timeout=timeout,
            until=until,
            template=template,
            query=query,
            proxy=proxy,
            delta=delta,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            ws=ws,
            alert_webhook=alert_webhook,
            alert_cmd=alert_cmd,
            alert_cooldown=alert_cooldown,
        )
    )


def _handle_data_output(
    d: DataResponse,
    *,
    query: str | None,
    delta: bool,
    tracker: DeltaTracker | None,
    fields: str | None,
    template: str | None,
    output_format: Format,
    console: Console,
) -> bool:
    """Process and display a single data response. Returns True if caller should stop."""
    if query:
        result = query_jsonpath(d.model_dump(), query)
        console.print(json.dumps(result, indent=2, default=str))
        return True

    if delta and tracker is not None:
        changes = tracker.update(d.model_dump())
        if changes:
            t = Table(show_header=True, header_style="bold magenta")
            t.add_column("Field", style="cyan")
            t.add_column("Value")
            for k, (old, new, diff) in changes.items():
                style = "green" if diff >= 0 else "red"
                t.add_row(
                    k,
                    f"[{style}]{old} \u2192 {new} (\u0394{diff:+.1f})[/{style}]",
                )
            console.print(t)
        return True

    filtered = _filter_fields(d, fields)
    if filtered:
        if output_format == Format.TABLE:
            t = Table(show_header=True, header_style="bold magenta")
            t.add_column("Field", style="cyan")
            t.add_column("Value", style="green")
            for k, v in filtered.items():
                t.add_row(k, str(v))
            console.print(t)
        else:
            console.print(json.dumps(filtered, indent=2, default=str))
        return True

    if template:
        from ..format.template import write_template

        write_template(d, console, template)
        return True

    write_data(d, output_format, console)
    return False


async def _data_async(
    watch: float | None,
    fields: str | None,
    format: str,
    host: str | None,
    request_timeout: float,
    until: str | None = None,
    template: str | None = None,
    query: str | None = None,
    proxy: str | None = None,
    delta: bool = False,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
    ws: bool = False,
    alert_webhook: str | None = None,
    alert_cmd: str | None = None,
    alert_cooldown: float = 0.0,
):
    console = Console()
    host = resolve_host(host)

    if ws and api_version != "v2":
        console.print("Error: --ws requires API v2 (default)", style="red")
        raise typer.Exit(code=1)

    if not ws and watch is not None and watch < 1.0:
        console.print(
            f"Warning: Polling interval {watch}s is below recommended minimum (1.0s).\n"
            "         Device may become unresponsive.",
            style="yellow",
        )
    output_format = get_format(format, console.is_terminal)

    webhook_urls = [alert_webhook] if alert_webhook else None
    alert_commands = [alert_cmd] if alert_cmd else None
    dispatcher = AlertDispatcher(
        webhook_urls=webhook_urls,
        commands=alert_commands,
        cooldown_seconds=alert_cooldown,
    )

    tracker: DeltaTracker | None = None
    if delta:
        if fields:
            tracker = DeltaTracker(fields=[f.strip() for f in fields.split(",")])
        else:
            tracker = DeltaTracker()

    if ws:
        ws_timeout = watch if watch is not None else 30.0
        wsc = WebSocketClient(
            host, token=token, verify_cert=not no_verify, timeout=ws_timeout
        )
        async with wsc as ws_conn:
            while True:
                msg = await ws_conn.receive_data()
                if msg is None:
                    continue
                m = MeasurementV2(**msg)
                d = convert_v2_measurement(m)

                if until and evaluate_until(d.model_dump(), until):
                    console.print(f"Condition met: {until}", style="green")
                    if dispatcher.configured:
                        await dispatcher.dispatch(until, d.model_dump())
                    if watch is None or not dispatcher.configured:
                        raise typer.Exit(code=10)
                    continue

                _handle_data_output(
                    d,
                    query=query,
                    delta=delta,
                    tracker=tracker,
                    fields=fields,
                    template=template,
                    output_format=output_format,
                    console=console,
                )
                if watch is None:
                    break
        return

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
                m = await c.get_json_v2("/api/measurement", MeasurementV2)
                d = convert_v2_measurement(m)
            else:
                d = await c.get_json("/api/v1/data", DataResponse)

            if until and evaluate_until(d.model_dump(), until):
                console.print(f"Condition met: {until}", style="green")
                if dispatcher.configured:
                    await dispatcher.dispatch(until, d.model_dump())
                if watch is None or not dispatcher.configured:
                    raise typer.Exit(code=10)
                await asyncio.sleep(watch)
                continue

            should_stop = _handle_data_output(
                d,
                query=query,
                delta=delta,
                tracker=tracker,
                fields=fields,
                template=template,
                output_format=output_format,
                console=console,
            )
            if should_stop:
                if watch is None:
                    return
                await asyncio.sleep(watch)
                continue

            if watch is None:
                break

            await asyncio.sleep(watch)
