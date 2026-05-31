"""Tests for the state CLI command."""

from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_state_help():
    result = runner.invoke(app, ["state", "--help"])
    assert result.exit_code == 0
    assert "state" in result.output.lower()


def test_state_read():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models.v2 import StateResponse

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_json_v2 = AsyncMock(
            return_value=StateResponse(
                power_on=True,
                switch_lock=False,
                brightness=100,
            )
        )

        result = runner.invoke(
            app,
            ["state", "--api-version", "v2", "--host", "192.168.1.1", "--token", "t"],
        )
        assert result.exit_code == 0
        assert "power_on" in result.output
        assert "switch_lock" in result.output
        assert "brightness" in result.output


def test_state_power_on():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"status": "ok"})

        result = runner.invoke(
            app,
            [
                "state",
                "--api-version",
                "v2",
                "--power-on",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        instance.put_json.assert_called_once_with("/api/state", {"power_on": True})


def test_state_power_off():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"status": "ok"})

        result = runner.invoke(
            app,
            [
                "state",
                "--api-version",
                "v2",
                "--power-off",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        instance.put_json.assert_called_once_with("/api/state", {"power_on": False})


def test_state_switch_lock():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"status": "ok"})

        result = runner.invoke(
            app,
            [
                "state",
                "--api-version",
                "v2",
                "--switch-lock",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        instance.put_json.assert_called_once_with("/api/state", {"switch_lock": True})


def test_state_switch_unlock():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"status": "ok"})

        result = runner.invoke(
            app,
            [
                "state",
                "--api-version",
                "v2",
                "--switch-unlock",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        instance.put_json.assert_called_once_with("/api/state", {"switch_lock": False})


def test_state_brightness():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"status": "ok"})

        result = runner.invoke(
            app,
            [
                "state",
                "--api-version",
                "v2",
                "--brightness",
                "50",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        instance.put_json.assert_called_once_with("/api/state", {"brightness": 50})


def test_state_multiple_ops():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.put_json = AsyncMock(return_value={"status": "ok"})

        result = runner.invoke(
            app,
            [
                "state",
                "--api-version",
                "v2",
                "--power-on",
                "--switch-lock",
                "--brightness",
                "75",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        instance.put_json.assert_called_once_with(
            "/api/state",
            {"power_on": True, "switch_lock": True, "brightness": 75},
        )


def test_state_error():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch("homewizard_cli.commands.state.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_json_v2 = AsyncMock(side_effect=HttpError(500, "/api/state"))

        result = runner.invoke(
            app,
            ["state", "--api-version", "v2", "--host", "192.168.1.1", "--token", "t"],
        )
        assert result.exit_code == 3
        assert "HTTP 500" in result.output
