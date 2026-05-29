# tests/test_discover_cmd.py
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


def test_discover_calls_discover_host():
    """Test that discover calls discover_host."""
    from unittest.mock import patch, AsyncMock

    with patch(
        "homewizard_cli.commands.discover.discover_host",
        new_callable=AsyncMock,
        return_value=("192.168.1.1", False),
    ):
        result = runner.invoke(app, ["discover"])
        assert result.exit_code == 0
        assert "192.168.1.1" in result.output
