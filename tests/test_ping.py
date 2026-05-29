from typer.testing import CliRunner
from homewizard_cli.main import app

runner = CliRunner()


def test_ping_help():
    result = runner.invoke(app, ["ping", "--help"])
    assert result.exit_code == 0
    assert "ping" in result.output.lower()
