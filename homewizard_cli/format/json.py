"""JSON output formatter."""

from rich.console import Console

from homewizard_cli.models import DataResponse
from homewizard_cli.util import _print_json


def write_json(data: DataResponse, console: Console):
    """Output data as pretty-printed JSON."""
    _print_json(console, data.model_dump(), indent=True)
