"""Output formatters for homewizard-cli."""

from collections.abc import Callable
from enum import StrEnum

from rich.console import Console

from .csv import write_csv
from .env import write_env
from .influx import write_influx
from .json import write_json
from .minimal import write_minimal
from .mqtt import write_mqtt
from .prometheus import write_prometheus
from .raw import write_raw
from .table import write_table
from .tsv import write_tsv


class Format(StrEnum):
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
    MQTT = "mqtt"


FORMAT_WRITERS: dict[Format, Callable] = {
    Format.AUTO: write_table,
    Format.JSON: write_json,
    Format.TABLE: write_table,
    Format.CSV: write_csv,
    Format.TSV: write_tsv,
    Format.INFLUX: write_influx,
    Format.PROMETHEUS: write_prometheus,
    Format.ENV: write_env,
    Format.MINIMAL: write_minimal,
    Format.RAW: write_raw,
    Format.MQTT: write_mqtt,
}


def get_format(format_str: str, is_tty: bool = False) -> Format:
    if format_str == "auto":
        return Format.TABLE if is_tty else Format.JSON
    return Format(format_str)


def write_data(data, format: Format, console: Console):
    if format == Format.AUTO:
        format = get_format("auto", console.is_terminal)
    writer = FORMAT_WRITERS.get(format, write_json)
    writer(data, console)
