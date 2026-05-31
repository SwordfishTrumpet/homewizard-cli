from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_gas_help():
    result = runner.invoke(app, ["gas", "--help"])
    assert result.exit_code == 0
    assert "gas" in result.output.lower()


def test_gas_default():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.gas.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=Measurement(total_gas_m3=1234.56))

        result = runner.invoke(app, ["gas", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "1,234.56" in result.output
        assert "m³" in result.output


def test_gas_full():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.gas.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            return_value=Measurement(
                total_gas_m3=1234.56,
                gas_timestamp=260528185009,
                gas_unique_id="GAS123",
            )
        )

        result = runner.invoke(app, ["gas", "--full", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "1,234.56" in result.output
        assert "GAS123" in result.output
        assert "Total:" in result.output


def test_gas_no_gas():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.gas.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=Measurement())

        result = runner.invoke(app, ["gas", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "—" in result.output


def test_gas_v1():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.gas.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json = AsyncMock(return_value=Measurement(total_gas_m3=1234.56))

        result = runner.invoke(
            app, ["gas", "--api-version", "v1", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "1,234.56" in result.output
        assert "m³" in result.output


def test_gas_watch():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.gas.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(return_value=Measurement(total_gas_m3=1234.56))

        with patch(
            "homewizard_cli.commands.gas.asyncio.sleep",
            side_effect=SystemExit(0),
        ):
            result = runner.invoke(
                app, ["gas", "--watch", "0.5", "--host", "192.168.1.1"]
            )

    assert result.exit_code == 0
    assert "1,234.56" in result.output
