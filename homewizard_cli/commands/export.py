"""homewizard-cli export command."""

import asyncio
import contextlib
import errno
import json
import os
import signal
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from ..alerting import AlertDispatcher
from ..client_factory import API_VERSIONS, resolve_client
from ..config import load_config, resolve_host
from ..errors import P1Error
from ..expr import evaluate_until
from ..format import Format, get_format, write_data
from ..models import Measurement
from ..state import DeltaTracker
from ..storage import _setup_store

app = typer.Typer()


def _install_signal_handlers(shutdown_event: asyncio.Event):
    """Install SIGINT and SIGTERM handlers that set shutdown_event."""
    loop = asyncio.get_running_loop()

    def _handler(signum, frame):
        loop.call_soon_threadsafe(shutdown_event.set)

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class _MetricsServer:
    """Tiny Prometheus metrics HTTP server."""

    def __init__(self):
        self.readings_total = 0
        self.errors_total = 0
        self.last_poll_timestamp = 0.0
        self._server = None

    async def _handle_request(self, reader, writer):
        request_data = await reader.read(1024)
        request = request_data.decode("utf-8", errors="ignore")
        if "GET /metrics" in request:
            body = self._format_metrics()
            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: text/plain; version=0.0.4\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"\r\n"
                f"{body}"
            )
        else:
            body = "404 Not Found\n"
            response = (
                f"HTTP/1.1 404 Not Found\r\nContent-Length: {len(body)}\r\n\r\n{body}"
            )
        writer.write(response.encode())
        await writer.drain()
        writer.close()

    def _format_metrics(self) -> str:
        lines = [
            "# HELP homewizard_readings_total Total readings exported",
            "# TYPE homewizard_readings_total counter",
            f"homewizard_readings_total {self.readings_total}",
            "",
            "# HELP homewizard_errors_total Total fetch/write errors",
            "# TYPE homewizard_errors_total counter",
            f"homewizard_errors_total {self.errors_total}",
            "",
            "# HELP homewizard_last_poll_timestamp_seconds "
            "Unix timestamp of last successful poll",
            "# TYPE homewizard_last_poll_timestamp_seconds gauge",
            f"homewizard_last_poll_timestamp_seconds {self.last_poll_timestamp}",
            "",
        ]
        return "\n".join(lines)

    async def start(self, port: int):
        self._server = await asyncio.start_server(
            self._handle_request, "127.0.0.1", port
        )

    async def stop(self):
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()


def _resolve_export_option(cli_value, config_value, default=None):
    """CLI arg overrides config, config overrides hardcoded default."""
    if cli_value is not None:
        return cli_value
    if config_value is not None:
        return config_value
    return default


@app.callback(invoke_without_command=True)
def export(
    format: str | None = typer.Option(None, "--format", "-f", help="Output format"),
    watch: float | None = typer.Option(None, "--watch", "-w", help="Poll interval"),
    file: str | None = typer.Option(None, "--file", help="Output file path"),
    rotate: str | None = typer.Option(
        None, "--rotate", help="File rotation strategy (daily, hourly)"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    broker: str | None = typer.Option(None, "--broker", help="MQTT broker URL"),
    topic: str | None = typer.Option(None, "--topic", help="MQTT topic"),
    qos: int | None = typer.Option(None, "--qos", help="MQTT QoS level"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
    skip_unchanged: bool | None = typer.Option(
        None, "--skip-unchanged", help="Skip write if data unchanged"
    ),
    fields: str | None = typer.Option(
        None, "--fields", help="Comma-separated field list"
    ),
    delta: bool | None = typer.Option(
        None, "--delta", help="Show only changed fields (requires --watch)"
    ),
    until: str | None = typer.Option(
        None, "--until", help="Exit when expression is true"
    ),
    metrics_port: int | None = typer.Option(
        None, "--metrics-port", help="Prometheus metrics HTTP port (0=disabled)"
    ),
    pid_file: str | None = typer.Option(
        None, "--pid-file", help="Path to write PID file"
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
    db: str | None = typer.Option(
        None, "--db", help="SQLite database path for historical storage"
    ),
    retain_days: int | None = typer.Option(
        None,
        "--retain-days",
        help="Auto-prune rows older than N days (requires --db)",
    ),
):
    """Export data in machine-readable formats."""
    asyncio.run(
        _export_async(
            format,
            watch,
            file,
            host,
            request_timeout=timeout,
            proxy=proxy,
            rotate=rotate,
            broker=broker,
            topic=topic,
            qos=qos,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            skip_unchanged=skip_unchanged,
            fields=fields,
            delta=delta,
            until=until,
            metrics_port=metrics_port,
            pid_file=pid_file,
            alert_webhook=alert_webhook,
            alert_cmd=alert_cmd,
            alert_cooldown=alert_cooldown,
            db=db,
            retain_days=retain_days,
        )
    )


def _filter_fields(data: Measurement, fields_str: str | None) -> dict | None:
    if not fields_str:
        return None
    wanted = {f.strip() for f in fields_str.split(",")}
    return {k: v for k, v in data.model_dump().items() if k in wanted}


async def _export_async(
    format: str | None,
    watch: float | None,
    file: str | None,
    host: str | None,
    request_timeout: float,
    proxy: str | None = None,
    rotate: str | None = None,
    broker: str | None = None,
    topic: str | None = None,
    qos: int | None = None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
    skip_unchanged: bool | None = None,
    fields: str | None = None,
    delta: bool | None = None,
    until: str | None = None,
    metrics_port: int | None = None,
    pid_file: str | None = None,
    alert_webhook: str | None = None,
    alert_cmd: str | None = None,
    alert_cooldown: float = 0.0,
    db: str | None = None,
    retain_days: int | None = None,
):
    console = Console()
    host = resolve_host(host)

    # Load config and resolve export-specific defaults
    cfg = load_config()
    export_cfg = cfg.export if cfg.export else None
    def cfg_val(key: str):
        return getattr(export_cfg, key, None) if export_cfg else None

    format = _resolve_export_option(format, cfg_val("format"), "influx")
    watch = _resolve_export_option(watch, cfg_val("watch"))
    file = _resolve_export_option(file, cfg_val("file"))
    rotate = _resolve_export_option(rotate, cfg_val("rotate"))
    broker = _resolve_export_option(broker, cfg_val("broker"))
    topic = _resolve_export_option(topic, cfg_val("topic"))
    qos = _resolve_export_option(qos, cfg_val("qos"))
    skip_unchanged = _resolve_export_option(
        skip_unchanged, cfg_val("skip_unchanged"), False
    )
    fields = _resolve_export_option(fields, cfg_val("fields"))
    delta = _resolve_export_option(delta, cfg_val("delta"), False)
    metrics_port = _resolve_export_option(metrics_port, cfg_val("metrics_port"), 0)
    pid_file = _resolve_export_option(pid_file, cfg_val("pid_file"))

    if watch is not None and watch < 1.0:
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

    # PID file handling
    pid_file_path = None
    if pid_file:
        pid_file_path = Path(pid_file)
        if pid_file_path.exists():
            try:
                old_pid = int(pid_file_path.read_text().strip())
            except (ValueError, OSError) as e:
                console.print(f"Error reading PID file {pid_file}: {e}", style="yellow")
            else:
                if _pid_is_alive(old_pid):
                    console.print(
                        f"PID file {pid_file} exists; process {old_pid} still running",
                        style="red",
                    )
                    raise typer.Exit(code=1)
        pid_file_path.write_text(str(os.getpid()))

    # Start metrics server
    metrics_server = None
    if metrics_port and metrics_port > 0:
        metrics_server = _MetricsServer()
        await metrics_server.start(metrics_port)

    file_handle = None
    file_path = None
    last_rotation_key = None
    file_stack = contextlib.ExitStack()

    if file:
        file_path = Path(file)
        file_handle = file_stack.enter_context(file_path.open("a"))

    def _check_rotation():
        nonlocal file_handle, last_rotation_key
        if rotate is None or file_handle is None:
            return
        now = datetime.now()
        if rotate == "daily":
            current_key = now.strftime("%Y-%m-%d")
        elif rotate == "hourly":
            current_key = now.strftime("%Y-%m-%dT%H")
        else:
            return

        if last_rotation_key is not None and current_key != last_rotation_key:
            rotated = file_path.with_name(f"{file_path.name}.{last_rotation_key}")
            try:
                file_handle.flush()
                os.fsync(file_handle.fileno())
                file_path.rename(rotated)
                file_handle = file_stack.enter_context(file_path.open("a"))
                console.print(f"  Rotated to {rotated.name}", style="green")
            except OSError as e:
                console.print(f"  Rotation error: {e}", style="red")
                try:
                    file_handle = file_stack.enter_context(file_path.open("a"))
                except OSError as reopen_err:
                    console.print(
                        f"Failed to reopen {file_path} after rotation: {reopen_err}",
                        style="red",
                    )
        last_rotation_key = current_key

    def _safe_write(buf: str) -> bool:
        if file_handle is None:
            return True
        try:
            file_handle.write(buf + "\n")
            file_handle.flush()
            return True
        except OSError as e:
            if e.errno == errno.ENOSPC:
                console.print("Disk full: write skipped", style="red")
            else:
                console.print(f"File write error: {e}", style="red")
            return False

    client = resolve_client(
        api_version,
        host,
        request_timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )

    backoff = 1.0
    max_backoff = 60.0
    tracker = DeltaTracker() if skip_unchanged else None
    delta_tracker = (
        DeltaTracker(fields=[f.strip() for f in fields.split(",")])
        if (delta and fields)
        else (DeltaTracker() if delta else None)
    )

    mqtt_client = None
    if format == "mqtt":
        if broker is None or topic is None:
            console.print(
                "--broker and --topic required for mqtt format",
                style="red",
            )
            return
        from ..format.mqtt import PersistentMqttClient

        mqtt_client = PersistentMqttClient(broker=broker, topic=topic, qos=qos or 0)

    shutdown_event = asyncio.Event()
    _install_signal_handlers(shutdown_event)

    try:
        async with client as c:
            store, serial = await _setup_store(db, api_version, c)
            prune_counter = 0
            while not shutdown_event.is_set():
                try:
                    if api_version == "v2":
                        data = await c.get_json_v2("/api/measurement", Measurement)
                    else:
                        data = await c.get_json("/api/v1/data", Measurement)
                    if store and serial:
                        store.append(data.model_dump(), serial)
                        prune_counter += 1
                        if retain_days is not None and prune_counter % 60 == 0:
                            deleted = store.retain(retain_days)
                            if deleted:
                                console.print(
                                    f"Pruned {deleted} old rows (>{retain_days}d)",
                                    style="green",
                                )
                except P1Error as e:
                    if metrics_server:
                        metrics_server.errors_total += 1
                    console.print(
                        f"Export fetch error: {e} (retrying in {backoff:.0f}s)",
                        style="red",
                    )
                    if watch is None:
                        raise
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(shutdown_event.wait(), timeout=backoff)
                    backoff = min(backoff * 2, max_backoff)
                    continue

                # Reset backoff after successful fetch
                backoff = 1.0

                if metrics_server:
                    metrics_server.readings_total += 1
                    metrics_server.last_poll_timestamp = datetime.now().timestamp()

                if until and evaluate_until(data.model_dump(), until):
                    console.print(f"Condition met: {until}", style="green")
                    if dispatcher.configured:
                        await dispatcher.dispatch(until, data.model_dump())
                    if watch is None or not dispatcher.configured:
                        raise typer.Exit(code=10)

                if tracker is not None:
                    is_first = not tracker._previous
                    changed = tracker.changed(data.model_dump())
                    if not is_first and not changed:
                        tracker.update(data.model_dump())
                        if watch is None:
                            break
                        with contextlib.suppress(TimeoutError):
                            await asyncio.wait_for(shutdown_event.wait(), timeout=watch)
                        continue
                    tracker.update(data.model_dump())

                if delta and delta_tracker is not None:
                    changes = delta_tracker.update(data.model_dump())
                    if changes:
                        from rich.table import Table

                        t = Table(show_header=True, header_style="bold magenta")
                        t.add_column("Field", style="cyan")
                        t.add_column("Value")
                        for k, (old, new, diff) in changes.items():
                            style = "green" if diff >= 0 else "red"
                            t.add_row(
                                k,
                                (
                                    f"[{style}]{old} \u2192 {new} "
                                    f"(\u0394{diff:+.1f})[/{style}]"
                                ),
                            )
                        console.print(t)
                    if watch is None:
                        break
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(shutdown_event.wait(), timeout=watch)
                    continue

                filtered = _filter_fields(data, fields)
                if filtered:
                    if output_format == Format.TABLE:
                        from rich.table import Table

                        t = Table(show_header=True, header_style="bold magenta")
                        t.add_column("Field", style="cyan")
                        t.add_column("Value", style="green")
                        for k, v in filtered.items():
                            t.add_row(k, str(v))
                        console.print(t)
                    else:
                        console.print(json.dumps(filtered, indent=2, default=str))
                    if file_handle:
                        from io import StringIO

                        buf = StringIO()
                        file_console = Console(file=buf, force_terminal=False)
                        file_console.print(json.dumps(filtered, indent=2, default=str))
                        _safe_write(buf.getvalue())
                    if watch is not None:
                        with contextlib.suppress(TimeoutError):
                            await asyncio.wait_for(shutdown_event.wait(), timeout=watch)
                        continue
                    break

                try:
                    if mqtt_client is not None:
                        ok = await mqtt_client.publish(data)
                        if not ok:
                            console.print(
                                f"MQTT publish failed ({mqtt_client.pending} buffered)",
                                style="yellow",
                            )
                    else:
                        if file_handle:
                            _check_rotation()

                            from io import StringIO

                            buf = StringIO()
                            file_console = Console(file=buf, force_terminal=False)
                            write_data(data, output_format, file_console)
                            _safe_write(buf.getvalue())
                        if not file:
                            write_data(data, output_format, console)
                except P1Error as e:
                    if metrics_server:
                        metrics_server.errors_total += 1
                    console.print(
                        f"Export write error: {e} (retrying in {backoff:.0f}s)",
                        style="red",
                    )
                    if watch is None:
                        raise
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(shutdown_event.wait(), timeout=backoff)
                    backoff = min(backoff * 2, max_backoff)
                    continue

                if watch is None:
                    break
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(shutdown_event.wait(), timeout=watch)
    finally:
        shutdown_event.set()
        if store:
            store.close()
        if mqtt_client is not None:
            await mqtt_client.close()
        file_stack.close()
        if metrics_server is not None:
            await metrics_server.stop()
        if pid_file_path is not None:
            try:
                pid_file_path.unlink()
            except OSError as e:
                console.print(
                    f"Error removing PID file {pid_file}: {e}", style="yellow"
                )
