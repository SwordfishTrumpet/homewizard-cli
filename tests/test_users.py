from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_users_help():
    result = runner.invoke(app, ["users", "--help"])
    assert result.exit_code == 0
    assert "users" in result.output.lower()


def test_users_list():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.users.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get = AsyncMock(return_value='[{"name": "alice"}, {"name": "bob"}]')

        result = runner.invoke(
            app,
            [
                "users",
                "list",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        assert "alice" in result.output
        assert "bob" in result.output


def test_users_list_not_list():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.users.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get = AsyncMock(return_value='{"error": "not a list"}')

        result = runner.invoke(
            app,
            [
                "users",
                "list",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        assert "not a list" in result.output


def test_users_delete():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.users.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.delete = AsyncMock(return_value={"deleted": True})

        result = runner.invoke(
            app,
            [
                "users",
                "delete",
                "--api-version",
                "v2",
                "--name",
                "alice",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 0
        assert "Deleted" in result.output


def test_users_delete_error():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch("homewizard_cli.commands.users.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.delete = AsyncMock(side_effect=HttpError(500, "/api/user"))

        result = runner.invoke(
            app,
            [
                "users",
                "delete",
                "--api-version",
                "v2",
                "--name",
                "alice",
                "--host",
                "192.168.1.1",
                "--token",
                "t",
            ],
        )
        assert result.exit_code == 3
        assert "HTTP 500" in result.output
