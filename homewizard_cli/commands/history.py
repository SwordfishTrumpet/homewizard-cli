"""homewizard-cli history command — retrospective queries."""

import asyncio
from datetime import datetime, timedelta

from ..util import _dumps_json

import typer
from rich.console import Console
from rich.table import Table

from ..config import CONFIG_DIR
from ..storage import MeasurementStore

DEFAULT_DB = str(CONFIG_DIR / "energy.db")

app = typer.Typer()


def _parse_range(range_str: str) -> tuple[str, str]:
    """Parse '2026-05-01..2026-05-29' into (start, end) ISO strings."""
    parts = range_str.split("..", 1)
    if len(parts) != 2:
        raise typer.BadParameter(
            "Range must be in format 'start..end' (e.g. '2026-05-01..2026-05-29')"
        )
    start_str, end_str = parts
    try:
        start_dt = datetime.strptime(start_str.strip(), "%Y-%m-%d")
        end_dt = datetime.strptime(end_str.strip(), "%Y-%m-%d")
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise typer.BadParameter(
            "Dates must be in YYYY-MM-DD format (e.g. '2026-05-01')"
        ) from None
    return start_dt.isoformat(), end_dt.isoformat()


def _get_time_range(
    yesterday: bool = False,
    today: bool = False,
    this_week: bool = False,
    this_month: bool = False,
    range_opt: str | None = None,
    since_last: bool = False,
    store: MeasurementStore | None = None,
) -> tuple[str | None, str | None]:
    now = datetime.now()
    if yesterday:
        start = (now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start.replace(hour=23, minute=59, second=59)
        return start.isoformat(), end.isoformat()
    if today:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.isoformat(), None
    if this_week:
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start.isoformat(), None
    if this_month:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start.isoformat(), None
    if range_opt:
        return _parse_range(range_opt)
    if since_last and store is not None:
        last = store.since_last()
        if last:
            return last.isoformat(), None
        return None, None
    # Default to today
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(), None


def _compute_comparison(
    current_rows: list[dict],
    prior_rows: list[dict],
    fields: list[str] | None,
) -> list[dict]:
    """Compute deltas and percentages between two result sets."""

    def _sum_field(rows: list[dict], field: str) -> float:
        return sum(r.get(field, 0) or 0 for r in rows)

    if not current_rows:
        return []

    # Determine which fields to compare
    compare_fields = fields or []
    if not compare_fields and current_rows:
        # Pick numeric fields
        skip = {
            "stored_at",
            "device_serial",
            "schema_version",
            "period",
            "wifi_ssid",
            "meter_model",
            "unique_id",
            "gas_unique_id",
            "text_message",
            "external",
        }
        for k in current_rows[0]:
            if k not in skip and isinstance(current_rows[0][k], (int, float)):
                compare_fields.append(k)

    results = []
    for field in compare_fields:
        curr_val = _sum_field(current_rows, field)
        prior_val = _sum_field(prior_rows, field) if prior_rows else 0.0
        delta = curr_val - prior_val
        pct = ((delta / prior_val) * 100) if prior_val else 0.0
        results.append(
            {
                "field": field,
                "current": round(curr_val, 3),
                "prior": round(prior_val, 3),
                "delta": round(delta, 3),
                "pct_change": round(pct, 1),
            }
        )
    return results


def _format_value(v: object) -> str:
    if v is None:
        return "\u2014"
    if isinstance(v, float):
        return f"{v:,.3f}"
    return str(v)


@app.callback(invoke_without_command=True)
def history(
    yesterday: bool = typer.Option(
        False, "--yesterday", help="All rows from yesterday"
    ),
    today: bool = typer.Option(False, "--today", help="All rows from today"),
    this_week: bool = typer.Option(
        False, "--this-week", help="This week (Mon 00:00 to now)"
    ),
    this_month: bool = typer.Option(
        False, "--this-month", help="This month (1st 00:00 to now)"
    ),
    range_opt: str | None = typer.Option(
        None, "--range", help="Date range 'start..end'"
    ),
    since_last: bool = typer.Option(
        False, "--since-last", help="From last stored timestamp to now"
    ),
    compare: str | None = typer.Option(
        None, "--compare", help="Compare period (last-week, last-month, last-year)"
    ),
    top: int | None = typer.Option(None, "--top", help="Show top N readings"),
    bottom: int | None = typer.Option(None, "--bottom", help="Show bottom N readings"),
    fields: str | None = typer.Option(
        None, "--fields", help="Comma-separated field names"
    ),
    device_id: str | None = typer.Option(
        None, "--device-id", help="Filter by device serial"
    ),
    list_devices: bool = typer.Option(
        False, "--list-devices", help="List all device serials in DB"
    ),
    agg: str | None = typer.Option(
        None, "--agg", help="Aggregation (hourly, daily, weekly, monthly)"
    ),
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format (table, json, csv, tsv)"
    ),
    db: str = typer.Option(
        DEFAULT_DB, "--db", help="SQLite database path", envvar="HW_DB"
    ),
    info: bool = typer.Option(False, "--info", help="Database metadata"),
    vacuum: bool = typer.Option(False, "--vacuum", help="Reclaim disk space"),
):
    """Query historical measurement data from a SQLite database."""
    asyncio.run(
        _history_async(
            yesterday=yesterday,
            today=today,
            this_week=this_week,
            this_month=this_month,
            range_opt=range_opt,
            since_last=since_last,
            compare=compare,
            top=top,
            bottom=bottom,
            fields=fields,
            device_id=device_id,
            list_devices=list_devices,
            agg=agg,
            format=format,
            db=db,
            info=info,
            vacuum=vacuum,
        )
    )


async def _history_async(
    yesterday: bool = False,
    today: bool = False,
    this_week: bool = False,
    this_month: bool = False,
    range_opt: str | None = None,
    since_last: bool = False,
    compare: str | None = None,
    top: int | None = None,
    bottom: int | None = None,
    fields: str | None = None,
    device_id: str | None = None,
    list_devices: bool = False,
    agg: str | None = None,
    format: str = "table",
    db: str = DEFAULT_DB,
    info: bool = False,
    vacuum: bool = False,
):
    console = Console()

    store = MeasurementStore(db)
    try:
        if list_devices:
            devices = store.list_devices()
            if format == "json":
                console.print(_dumps_json(devices, indent=True))
            else:
                t = Table(show_header=True, header_style="bold magenta")
                t.add_column("Device Serial", style="cyan")
                for d in devices:
                    t.add_row(d)
                console.print(t)
            return

        if info:
            meta = store.info()
            if format == "json":
                console.print(_dumps_json(meta, indent=True))
            else:
                console.print(f"Database:    {db}")
                console.print(f"Size:        {_format_file_size(meta['file_size_bytes'])}")
                console.print(f"Rows:        {meta['row_count']:,}")
                devices_str = ", ".join(meta["devices"]) if meta["devices"] else "none"
                console.print(f"Devices:     {len(meta['devices'])} ({devices_str})")
                start_str = meta["date_start"] or "\u2014"
                end_str = meta["date_end"] or "\u2014"
                console.print(f"Date range:  {start_str} .. {end_str}")
                console.print(f"Completeness: {meta['completeness_pct']}%")
            return

        if vacuum:
            store.vacuum()
            console.print("Database vacuumed.", style="green")
            return

        field_list: list[str] | None = None
        if fields:
            field_list = [f.strip() for f in fields.split(",")]

        start, end = _get_time_range(
            yesterday=yesterday,
            today=today,
            this_week=this_week,
            this_month=this_month,
            range_opt=range_opt,
            since_last=since_last,
            store=store,
        )

        top_n: int | None = None
        if top is not None:
            top_n = top
        elif bottom is not None:
            top_n = -bottom

        if compare:
            _run_comparison(
                store, start, end, compare, field_list, device_id, format, console, db
            )
            return

        rows = store.query(
            start=start,
            end=end,
            fields=field_list,
            agg=agg,
            device_serial=device_id,
            top_n=top_n,
        )

        if not rows:
            console.print("No data found.", style="yellow")
            return

        if format == "json":
            console.print(_dumps_json(rows, indent=True))
        elif format == "csv":
            _print_csv(rows, console)
        elif format == "tsv":
            _print_tsv(rows, console)
        else:
            _print_table(rows, console)
    finally:
        store.close()


def _run_comparison(
    store: MeasurementStore,
    start: str | None,
    end: str | None,
    compare: str,
    fields: list[str] | None,
    device_id: str | None,
    format: str,
    console: Console,
    db: str,
) -> None:
    now = datetime.now()
    if start is None:
        console.print("No time range specified for comparison.", style="red")
        return

    # Determine prior period
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end) if end else now
    except (ValueError, TypeError):
        console.print("Invalid date range.", style="red")
        return

    if compare == "last-week":
        prior_start = start_dt - timedelta(weeks=1)
        prior_end = end_dt - timedelta(weeks=1)
    elif compare == "last-month":
        prior_start = start_dt - timedelta(days=30)
        prior_end = end_dt - timedelta(days=30)
    elif compare == "last-year":
        prior_start = start_dt - timedelta(days=365)
        prior_end = end_dt - timedelta(days=365)
    else:
        console.print(f"Unknown compare period: {compare}", style="red")
        return

    current_rows = store.query(
        start=start, end=end, fields=fields, device_serial=device_id
    )
    prior_rows = store.query(
        start=prior_start.isoformat(),
        end=prior_end.isoformat(),
        fields=fields,
        device_serial=device_id,
    )

    comparison = _compute_comparison(current_rows, prior_rows, fields)
    if not comparison:
        console.print("No data for comparison.", style="yellow")
        return

    if format == "json":
        console.print(_dumps_json(comparison, indent=True))
    else:
        t = Table(show_header=True, header_style="bold magenta")
        t.add_column("Field", style="cyan")
        t.add_column("Current", justify="right")
        t.add_column("Prior", justify="right")
        t.add_column("Delta", justify="right")
        t.add_column("Change", justify="right")
        for row in comparison:
            delta_str = f"+{row['delta']}" if row["delta"] >= 0 else str(row["delta"])
            pct_str = (
                f"+{row['pct_change']}%"
                if row["pct_change"] >= 0
                else f"{row['pct_change']}%"
            )
            t.add_row(
                row["field"],
                _format_value(row["current"]),
                _format_value(row["prior"]),
                delta_str,
                pct_str,
            )
        console.print(t)


def _print_table(rows: list[dict], console: Console) -> None:
    if not rows:
        return
    t = Table(show_header=True, header_style="bold magenta")
    for k in rows[0]:
        t.add_column(
            k, style="cyan" if k in ("period", "stored_at", "device_serial") else None
        )
    for row in rows:
        t.add_row(*[_format_value(v) for v in row.values()])
    console.print(t)


def _print_csv(rows: list[dict], console: Console) -> None:
    if not rows:
        return
    headers = list(rows[0].keys())
    console.print(",".join(headers))
    for row in rows:
        console.print(",".join(_format_value(row[h]) for h in headers))


def _print_tsv(rows: list[dict], console: Console) -> None:
    if not rows:
        return
    headers = list(rows[0].keys())
    console.print("\t".join(headers))
    for row in rows:
        console.print("\t".join(_format_value(row[h]) for h in headers))


def _format_file_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f} MB"
