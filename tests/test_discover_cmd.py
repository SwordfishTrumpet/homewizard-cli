# tests/test_discover_cmd.py
import pytest
from typer.testing import CliRunner
from homewizard_cli.main import app

runner = CliRunner()


def test_discover_help():
    result = runner.invoke(app, ["discover", "--help"])
    assert result.exit_code == 0
    assert "discover" in result.output.lower()


def test_discover_verbose_help():
    result = runner.invoke(app, ["discover", "--verbose", "--help"])
    assert result.exit_code == 0
