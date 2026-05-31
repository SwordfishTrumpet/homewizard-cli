"""JSON output formatter."""

import json

from rich.console import Console

from homewizard_cli.models import DataResponse


def write_json(data: DataResponse, console: Console):
    """Output data as pretty-printed JSON."""
    output = json.dumps(data.model_dump(), indent=2, default=str)
    console.print(output)
