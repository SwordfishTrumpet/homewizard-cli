import pytest
from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_identify_help():
    result = runner.invoke(app, ["identify", "--help"])
    assert result.exit_code == 0
    assert "identify" in result.output.lower()


def test_identify_default():
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.identify.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.put_json = AsyncMock(return_value={})

        result = runner.invoke(
            app, ["identify", "--api-version", "v2", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "LED blink triggered" in result.output


def test_identify_count():
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.identify.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.put_json = AsyncMock(return_value={})

        result = runner.invoke(
            app,
            [
                "identify",
                "--api-version",
                "v2",
                "--count",
                "3",
                "--host",
                "192.168.1.1",
            ],
        )
        assert result.exit_code == 0
        assert "3x" in result.output
        assert client.put_json.call_count == 3


@pytest.mark.parametrize("status", [401, 403])
def test_identify_forbidden_write_is_not_reported_as_success(status):
    """#35: a 401/403 on the identify write must fail loudly."""
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch(
        "homewizard_cli.commands.identify.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.put_json = AsyncMock(side_effect=HttpError(status, "/api/system/identify"))

        result = runner.invoke(
            app, ["identify", "--api-version", "v2", "--host", "192.168.1.1"]
        )

    assert result.exit_code != 0
    assert "LED blink triggered" not in result.output
    client.put_json.assert_called_once()
