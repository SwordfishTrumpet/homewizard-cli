"""homewizard-cli config command."""

import typer
from rich.console import Console

from ..config import validate_config

app = typer.Typer()


@app.callback(invoke_without_command=True)
def config(
    validate: bool = typer.Option(False, "--validate", help="Validate config file"),
    host: str | None = typer.Option(
        None, "--host", "-H", help="P1 meter IP (ignored for config)"
    ),
):
    """Manage homewizard-cli configuration."""
    console = Console()
    if validate:
        issues = validate_config()
        for issue in issues:
            if "valid" in issue.lower() and "invalid" not in issue.lower():
                console.print(f"\u2713 {issue}", style="green")
            elif "not found" in issue.lower():
                console.print(f"\u2717 {issue}", style="yellow")
            else:
                console.print(f"\u2717 {issue}", style="red")
    else:
        console.print("Use --validate to check config file", style="cyan")
