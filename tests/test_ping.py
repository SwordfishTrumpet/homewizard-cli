from unittest.mock import patch

from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()

_OK_OUTPUT = (
    "PING 192.168.1.1 (192.168.1.1) 56(84) bytes of data.\n"
    "64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=2.34 ms\n"
)


def test_ping_help():
    result = runner.invoke(app, ["ping", "--help"])
    assert result.exit_code == 0
    assert "icmp" in result.output.lower()


def test_ping_ok():
    with patch("homewizard_cli.commands.ping.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = _OK_OUTPUT

        result = runner.invoke(app, ["ping", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "OK" in result.output
        assert "2.34ms" in result.output
        assert "192.168.1.1" in result.output


def test_ping_fail():
    with patch("homewizard_cli.commands.ping.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""

        result = runner.invoke(app, ["ping", "--host", "192.168.1.1"])
        assert result.exit_code == 2
        assert "FAIL" in result.output


def test_ping_timeout():
    with patch("homewizard_cli.commands.ping.subprocess.run") as mock_run:
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("ping", 5)

        result = runner.invoke(app, ["ping", "--host", "192.168.1.1"])
        assert result.exit_code == 2
        assert "FAIL" in result.output


def test_ping_quiet():
    with patch("homewizard_cli.commands.ping.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = _OK_OUTPUT

        result = runner.invoke(app, ["ping", "--quiet", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert result.output == ""
