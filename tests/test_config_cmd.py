from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_config_validate_help():
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0
    assert "config" in result.output.lower()


def test_config_validate_ok():
    from unittest.mock import patch

    with patch(
        "homewizard_cli.commands.config.validate_config",
        return_value=["Config file is valid"],
    ):
        result = runner.invoke(app, ["config", "--validate"])
        assert result.exit_code == 0
        assert "Config file is valid" in result.output


def test_config_validate_invalid():
    from unittest.mock import patch

    with patch(
        "homewizard_cli.commands.config.validate_config",
        return_value=["Invalid TOML: bad syntax"],
    ):
        result = runner.invoke(app, ["config", "--validate"])
        assert result.exit_code == 0
        assert "Invalid TOML" in result.output


def test_config_validate_not_found():
    from unittest.mock import patch

    with patch(
        "homewizard_cli.commands.config.validate_config",
        return_value=["Config file not found at /fake/path"],
    ):
        result = runner.invoke(app, ["config", "--validate"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()


def test_config_host_noop():
    """--host should be accepted on config even though it's ignored."""
    result = runner.invoke(app, ["config", "--host", "192.168.1.1"])
    assert result.exit_code == 0
