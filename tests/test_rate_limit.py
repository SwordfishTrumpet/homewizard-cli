from typer.testing import CliRunner
from homewizard_cli.main import app

runner = CliRunner()


def test_data_rate_warning_help():
    result = runner.invoke(app, ["data", "--watch", "0.5", "--help"])
    assert result.exit_code == 0
