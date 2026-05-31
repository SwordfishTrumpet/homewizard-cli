from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_reboot_help():
    result = runner.invoke(app, ["reboot", "--help"])
    assert result.exit_code == 0
    assert "reboot" in result.output.lower()


def test_reboot_default():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.reboot.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"success": True})

        result = runner.invoke(
            app, ["reboot", "--api-version", "v2", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "Reboot result" in result.output


def test_reboot_error():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch("homewizard_cli.commands.reboot.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(side_effect=HttpError(500, "/api/system/reboot"))

        result = runner.invoke(
            app, ["reboot", "--api-version", "v2", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 3
        assert "HTTP 500" in result.output
