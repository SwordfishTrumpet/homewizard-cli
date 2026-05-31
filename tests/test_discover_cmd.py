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
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.discover.discover_host",
        new_callable=AsyncMock,
        return_value=("192.168.1.1", False),
    ):
        result = runner.invoke(app, ["discover"])
        assert result.exit_code == 0
        assert "192.168.1.1" in result.output


def test_discover_all():
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.discover.discover_all_hosts",
        new_callable=AsyncMock,
        return_value=[
            {
                "host": "192.168.1.1",
                "product_type": "HWE-P1",
                "serial": "ABC",
                "product_name": "P1",
            }
        ],
    ):
        result = runner.invoke(app, ["discover", "--all"])
        assert result.exit_code == 0
        assert "192.168.1.1" in result.output
        assert "HWE-P1" in result.output


def test_discover_all_no_devices():
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.discover.discover_all_hosts",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = runner.invoke(app, ["discover", "--all"])
        assert result.exit_code == 0
        assert "No HomeWizard devices found" in result.output


def test_discover_all_save_warning():
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.discover.discover_all_hosts",
        new_callable=AsyncMock,
        return_value=[
            {
                "host": "192.168.1.1",
                "product_type": "HWE-P1",
                "serial": "ABC",
                "product_name": "P1",
            }
        ],
    ):
        result = runner.invoke(app, ["discover", "--all", "--save"])
        assert result.exit_code == 0
        assert "ignored" in result.output.lower()


def test_discover_save():
    from unittest.mock import AsyncMock, patch

    with (
        patch(
            "homewizard_cli.commands.discover.discover_host",
            new_callable=AsyncMock,
            return_value=("192.168.1.1", False),
        ),
        patch("homewizard_cli.commands.discover._save_cache"),
    ):
        result = runner.invoke(app, ["discover", "--save"])
        assert result.exit_code == 0
        assert "saved" in result.output.lower()
