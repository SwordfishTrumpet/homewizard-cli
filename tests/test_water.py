from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_water_help():
    result = runner.invoke(app, ["water", "--help"])
    assert result.exit_code == 0
    assert "water" in result.output.lower()


def test_water_no_meter():
    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.water.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=Measurement())

        result = runner.invoke(app, ["water"])
        assert result.exit_code == 0
        assert "No water meter found" in result.output


def test_water_with_meter():
    from homewizard_cli.models import ExternalDevice, Measurement

    measurement = Measurement(
        external=[
            ExternalDevice(
                unique_id="w1",
                type="water_meter",
                timestamp=260529120000,
                value=1234.0,
                unit="m3",
            )
        ]
    )

    with patch(
        "homewizard_cli.commands.water.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=measurement)

        result = runner.invoke(app, ["water"])
        assert result.exit_code == 0
        assert "1,234.00 m" in result.output


def test_water_full_details():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import ExternalDevice, Measurement

    measurement = Measurement(
        external=[
            ExternalDevice(
                unique_id="w1",
                type="water_meter",
                timestamp=260529120000,
                value=1234.0,
                unit="m3",
            )
        ]
    )

    with patch(
        "homewizard_cli.commands.water.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=measurement)

        result = runner.invoke(app, ["water", "--full", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "Total:" in result.output
        assert "1,234.00" in result.output
        assert "Meter ID:" in result.output
        assert "w1" in result.output


def test_water_watch():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import ExternalDevice, Measurement

    measurement = Measurement(
        external=[
            ExternalDevice(
                unique_id="w1",
                type="water_meter",
                timestamp=260529120000,
                value=1234.0,
                unit="m3",
            )
        ]
    )

    with patch(
        "homewizard_cli.commands.water.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=measurement)

        with patch(
            "homewizard_cli.commands.water.asyncio.sleep",
            side_effect=SystemExit(0),
        ):
            result = runner.invoke(
                app, ["water", "--watch", "0.5", "--host", "192.168.1.1"]
            )

    assert result.exit_code == 0
    assert "1,234.00" in result.output


def test_water_full_watch():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import ExternalDevice, Measurement

    measurement = Measurement(
        external=[
            ExternalDevice(
                unique_id="w1",
                type="water_meter",
                timestamp=260529120000,
                value=1234.0,
                unit="m3",
            )
        ]
    )

    with patch(
        "homewizard_cli.commands.water.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=measurement)

        with patch(
            "homewizard_cli.commands.water.asyncio.sleep",
            side_effect=SystemExit(0),
        ):
            result = runner.invoke(
                app,
                ["water", "--full", "--watch", "0.5", "--host", "192.168.1.1"],
            )

    assert result.exit_code == 0
    assert "Total:" in result.output
    assert "1,234.00" in result.output
    assert "Meter ID:" in result.output
