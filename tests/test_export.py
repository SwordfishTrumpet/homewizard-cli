# tests/test_export.py
from typer.testing import CliRunner
from homewizard_cli.main import app

runner = CliRunner()


def test_export_help():
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "export" in result.output.lower()


def test_export_format_help():
    result = runner.invoke(app, ["export", "--format", "influx", "--help"])
    assert result.exit_code == 0
