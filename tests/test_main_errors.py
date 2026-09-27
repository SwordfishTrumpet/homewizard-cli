from unittest.mock import patch

from typer.testing import CliRunner

from homewizard_cli.errors import P1Error
from homewizard_cli.main import main

runner = CliRunner()



def test_main_p1_error(capsys):
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = P1Error("device error", code=5)
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 5
    captured = capsys.readouterr()
    assert "device error" in captured.err


def test_main_p1_error_with_details(capsys):
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = P1Error("device error", code=5, details="more info")
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 5
    captured = capsys.readouterr()
    assert "device error" in captured.err
    assert "more info" in captured.err


def test_main_generic_exception(capsys):
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = Exception("unexpected")
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "unexpected" in captured.err


def test_main_system_exit():
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = SystemExit(0)
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_global_options_before_subcommand_warn():
    """MED-1: global options before a subcommand must not be silently ignored."""
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.main import app
    from homewizard_cli.models import Measurement

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get_json_v2 = AsyncMock(return_value=Measurement(active_power_w=500.0))

    with patch("homewizard_cli.commands.data.resolve_client", return_value=client):
        result = runner.invoke(app, ["--host", "192.168.1.1", "data", "--format", "json"])
    assert result.exit_code == 0
    assert "after the subcommand" in result.stderr


def test_global_options_alone_still_work():
    """The default (no-subcommand) path must keep honoring global options."""
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.main import app
    from homewizard_cli.models import Measurement

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get_json_v2 = AsyncMock(return_value=Measurement(active_power_w=500.0))

    with patch("homewizard_cli.main.resolve_client", return_value=client):
        result = runner.invoke(app, ["--host", "192.168.1.1", "--format", "json"])
    assert result.exit_code == 0
    assert "500.0" in result.output
