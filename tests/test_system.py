from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_system_help():
    result = runner.invoke(app, ["system", "--help"])
    assert result.exit_code == 0
    assert "system" in result.output.lower()


def test_system_read():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models.v2 import SystemV2

    with patch(
        "homewizard_cli.commands.system.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            return_value=SystemV2(
                cloud_enabled=True,
                wifi_ssid="MyWifi",
                wifi_rssi_db=-50.0,
            )
        )

        result = runner.invoke(app, ["system", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "cloud_enabled" in result.output
        assert "MyWifi" in result.output


def test_system_write_cloud():
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.system.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.put_json = AsyncMock(return_value={"cloud_enabled": True})

        result = runner.invoke(app, ["system", "--cloud", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "cloud_enabled" in result.output


def test_system_write_led():
    from unittest.mock import AsyncMock, patch

    with patch(
        "homewizard_cli.commands.system.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.put_json = AsyncMock(return_value={"status_led_brightness_pct": 50})

        result = runner.invoke(
            app, ["system", "--led-brightness", "50", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "50" in result.output


def test_system_cloud_toggle():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models.v2 import SystemV2

    with patch(
        "homewizard_cli.commands.system.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=SystemV2(cloud_enabled=True))
        client.put_json = AsyncMock(return_value={"cloud_enabled": False})

        result = runner.invoke(
            app, ["system", "--cloud-toggle", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "cloud_enabled" in result.output


def test_system_v1():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import SystemResponse

    with patch(
        "homewizard_cli.commands.system.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json = AsyncMock(return_value=SystemResponse(cloud_enabled=True))

        result = runner.invoke(
            app, ["system", "--api-version", "v1", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "cloud_enabled:" in result.output
        assert "True" in result.output


def test_system_cloud_toggle_disabled():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models.v2 import SystemV2

    with patch(
        "homewizard_cli.commands.system.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=SystemV2(cloud_enabled=False))
        client.put_json = AsyncMock(return_value={"cloud_enabled": True})

        result = runner.invoke(
            app, ["system", "--cloud-toggle", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "cloud_enabled" in result.output
        assert "true" in result.output


def test_system_write_error():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.errors import HttpError

    with patch(
        "homewizard_cli.commands.system.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.put_json = AsyncMock(side_effect=HttpError(500, "/api/system"))

        result = runner.invoke(app, ["system", "--cloud", "--host", "192.168.1.1"])
        assert result.exit_code != 0
        assert "HTTP 500" in result.output or "HTTP 500" in str(result.exception or "")
