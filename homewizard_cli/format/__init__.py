"""Output formatters for homewizard-cli."""

from enum import Enum
from typing import Dict, Callable
from rich.console import Console

from .json import write_json
from .table import write_table
from .minimal import write_minimal


class Format(str, Enum):
    """Output format options."""

    AUTO = "auto"
    JSON = "json"
    TABLE = "table"
    MINIMAL = "minimal"


# Map format to writer function
FORMAT_WRITERS: Dict[Format, Callable] = {
    Format.JSON: write_json,
    Format.TABLE: write_table,
    Format.MINIMAL: write_minimal,
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
