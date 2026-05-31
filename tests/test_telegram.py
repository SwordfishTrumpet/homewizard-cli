from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_telegram_help():
    result = runner.invoke(app, ["telegram", "--help"])
    assert result.exit_code == 0
    assert "telegram" in result.output.lower()


def test_telegram_validate_help():
    result = runner.invoke(app, ["telegram", "--validate", "--help"])
    assert result.exit_code == 0


def test_telegram_obis_help():
    result = runner.invoke(app, ["telegram", "--help"])
    assert result.exit_code == 0
    assert "--obis" in result.output
