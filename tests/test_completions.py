from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_install_completion_help():
    result = runner.invoke(app, ["--install-completion", "--help"])
    assert result.exit_code == 0


def test_show_completion_help():
    result = runner.invoke(app, ["--show-completion", "--help"])
    assert result.exit_code == 0
