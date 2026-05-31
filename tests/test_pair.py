from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_pair_help():
    result = runner.invoke(app, ["pair", "--help"])
    assert result.exit_code == 0
    assert "pair" in result.output.lower()


def test_pair_default():
    from unittest.mock import AsyncMock, patch

    with patch("homewizard_cli.commands.pair.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.pair = AsyncMock(return_value={"name": "local/cli", "token": "abc123"})

        result = runner.invoke(
            app, ["pair", "--api-version", "v2", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "local/cli" in result.output
        assert "abc123" in result.output


def test_pair_403():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch("homewizard_cli.commands.pair.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.pair = AsyncMock(side_effect=HttpError(403, "/api/user"))

        result = runner.invoke(
            app, ["pair", "--api-version", "v2", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "Press the button" in result.output


def test_pair_other_error():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch("homewizard_cli.commands.pair.P1ClientV2") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.pair = AsyncMock(side_effect=HttpError(500, "/api/user"))

        result = runner.invoke(
            app, ["pair", "--api-version", "v2", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 3
        assert "HTTP 500" in result.output
