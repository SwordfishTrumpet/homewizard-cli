"""Output formatters for homewizard-cli."""

from enum import Enum
from typing import Dict, Callable
from rich.console import Console

from .csv import write_csv
from .env import write_env
from .influx import write_influx
from .json import write_json
from .minimal import write_minimal
from .prometheus import write_prometheus
from .raw import write_raw
from .table import write_table
from .template import write_template
from .tsv import write_tsv


class Format(str, Enum):
    """Output format options."""

    AUTO = "auto"
    JSON = "json"
    TABLE = "table"
    CSV = "csv"
    TSV = "tsv"
    INFLUX = "influx"
    PROMETHEUS = "prometheus"
    ENV = "env"
    MINIMAL = "minimal"
    RAW = "raw"
    TEMPLATE = "template"


FORMAT_WRITERS: Dict[Format, Callable] = {
    Format.JSON: write_json,
    Format.TABLE: write_table,
    Format.CSV: write_csv,
    Format.TSV: write_tsv,
    Format.INFLUX: write_influx,
    Format.PROMETHEUS: write_prometheus,
    Format.ENV: write_env,
    Format.MINIMAL: write_minimal,
    Format.RAW: write_raw,
    Format.TEMPLATE: write_template,
}


def get_format(format_str: str, is_tty: bool = False) -> Format:
    """Determine output format from string and TTY status."""
    if format_str == "auto":
        return Format.TABLE if is_tty else Format.JSON
    return Format(format_str)


def write_data(data, format: Format, console: Console):
    """Write data using the specified format."""
    writer = FORMAT_WRITERS.get(format, write_json)
    writer(data, console)
