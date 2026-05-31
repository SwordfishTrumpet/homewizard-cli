"""Template output formatter."""

import re

from rich.console import Console

from homewizard_cli.models import DataResponse

_TEMPLATE_RE = re.compile(r"\{\{\.([a-zA-Z_][a-zA-Z0-9_]*)\}\}")


def write_template(data: DataResponse, console: Console, template: str = ""):
    """Output data using a Go-style template string."""
    data_dict = data.model_dump()

    def _replace(m):
        key = m.group(1)
        value = data_dict.get(key)
        if value is None:
            return ""
        return str(value)

    output = _TEMPLATE_RE.sub(_replace, template)
    console.print(output)
