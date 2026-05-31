from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_batteries_help():
    result = runner.invoke(app, ["batteries", "--help"])
    assert result.exit_code == 0
    assert "batteries" in result.output.lower()


def test_batteries_read():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models.v2 import BatteryState

    with patch("homewizard_cli.commands.batteries.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_json_v2 = AsyncMock(
            return_value=BatteryState(
                mode="zero",
                battery_count=2,
                power_w=100.0,
            )
        )

        result = runner.invoke(
            app,
            [
                "batteries",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        assert "zero" in result.output
        assert "100.0" in result.output


def test_batteries_write():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.batteries.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"mode": "to_full"})

        result = runner.invoke(
            app,
            [
                "batteries",
                "--api-version",
                "v2",
                "--mode",
                "to_full",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        assert "to_full" in result.output


def test_batteries_error():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch("homewizard_cli.commands.batteries.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_json_v2 = AsyncMock(side_effect=HttpError(500, "/api/batteries"))

        result = runner.invoke(
            app,
            [
                "batteries",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 3
        assert "HTTP 500" in result.output
