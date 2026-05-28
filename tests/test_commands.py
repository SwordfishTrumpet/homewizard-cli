import pytest
from unittest.mock import AsyncMock, patch
from typer.testing import CliRunner
from homewizard_cli.main import app
from homewizard_cli.models import DataResponse

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "homewizard-cli version:" in result.output


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "HomeWizard P1 Meter CLI" in result.output


def test_data_help():
    result = runner.invoke(app, ["data", "--help"])
    assert result.exit_code == 0
    assert "Fetch and display" in result.output


def test_power_help():
    result = runner.invoke(app, ["power", "--help"])
    assert result.exit_code == 0
    assert "real-time power" in result.output
