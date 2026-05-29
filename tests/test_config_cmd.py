from typer.testing import CliRunner
from homewizard_cli.main import app

runner = CliRunner()


def test_config_validate_help():
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0
    assert "config" in result.output.lower()
