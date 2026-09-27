# tests/test_telegram_func.py
import asyncio
import json
from io import StringIO
from unittest.mock import AsyncMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from homewizard_cli.commands.telegram import (
    _parse_telegram,
    _telegram_async,
    _validate_and_print,
)
from homewizard_cli.main import app
from homewizard_cli.util import _crc16

runner = CliRunner()


def _make_valid_telegram(lines: list[str]) -> str:
    """Build a DSMR telegram with a valid CRC.

    Per the DSMR spec the CRC is computed over the telegram content
    up to and INCLUDING the terminating ``!`` (see dsmr_parser reference:
    ``re.search(r'/\\/.+\\!', telegram, re.DOTALL)``).
    """
    body = "\n".join(lines)
    if body and not body.endswith("\n"):
        body += "\n"
    crc = _crc16((body + "!").encode("ascii"))
    return body + f"!{crc:04X}"


def _make_client_mock(telegram: str, api_version: str = "v2"):
    """Create a mock client that returns a fixed telegram."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=telegram)
    return client


# ---------------------------------------------------------------------------
# _parse_telegram unit tests
# ---------------------------------------------------------------------------


def test_parse_telegram_valid():
    body_lines = [
        "/TEST",
        "1-0:1.8.1(002052.366*kWh)",
        "0-0:1.0.0(220815164518W)",
    ]
    raw = _make_valid_telegram(body_lines)
    result = _parse_telegram(raw)
    assert result["header"] == "/TEST"
    assert result["timestamp"] == "220815164518W"
    assert result["obis"]["1-0:1.8.1"] == "002052.366*kWh"
    assert result["valid"] is True


def test_parse_telegram_invalid_crc():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    body = "\n".join(body_lines) + "\n"
    raw = body + "!0000"
    result = _parse_telegram(raw)
    assert result["valid"] is False
    assert result["crc"] == "0000"


def test_parse_telegram_missing_crc():
    raw = "/TEST\n1-0:1.8.1(002052.366*kWh)"
    result = _parse_telegram(raw)
    assert result["crc"] == ""
    assert result["valid"] is False


def test_parse_telegram_empty():
    result = _parse_telegram("")
    assert result["header"] == ""
    assert result["timestamp"] == ""
    assert result["obis"] == {}
    assert result["valid"] is False


def test_parse_telegram_no_obis():
    raw = _make_valid_telegram(["/TEST"])
    result = _parse_telegram(raw)
    assert result["header"] == "/TEST"
    assert result["obis"] == {}
    assert result["valid"] is True


def test_parse_telegram_multiline_value():
    """Values that span lines are not handled; only the first ( is used."""
    raw = "/TEST\n1-0:1.8.1(002052.366*kWh)\n!0000"
    result = _parse_telegram(raw)
    assert result["obis"]["1-0:1.8.1"] == "002052.366*kWh"


# ---------------------------------------------------------------------------
# _validate_and_print unit tests
# ---------------------------------------------------------------------------


def _strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_validate_and_print_valid():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    _validate_and_print(raw, console)
    output = buf.getvalue()
    assert "Valid" in output
    assert "CRC:" in output


def test_validate_and_print_invalid():
    raw = "/TEST\n1-0:1.8.1(002052.366*kWh)\n!0000"
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    _validate_and_print(raw, console)
    output = _strip_ansi(buf.getvalue())
    assert "Invalid" in output
    assert "received 0000" in output


def test_validate_and_print_missing_crc():
    raw = "/TEST\n1-0:1.8.1(002052.366*kWh)"
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    _validate_and_print(raw, console)
    output = _strip_ansi(buf.getvalue())
    assert "No CRC found" in output
    assert "1-0:1.8.1" in output


def test_validate_and_print_empty():
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    _validate_and_print("", console)
    output = buf.getvalue()
    assert "Empty telegram" in output


# ---------------------------------------------------------------------------
# CLI --explain
# ---------------------------------------------------------------------------


def test_telegram_explain_known():
    result = runner.invoke(app, ["telegram", "--explain", "1-0:1.8.1"])
    assert result.exit_code == 0
    assert "1-0:1.8.1" in result.output
    assert "import" in result.output.lower()


def test_telegram_explain_unknown():
    result = runner.invoke(app, ["telegram", "--explain", "9-9:9.9.9"])
    assert result.exit_code == 0
    assert "Unknown OBIS code" in result.output


# ---------------------------------------------------------------------------
# CLI --obis
# ---------------------------------------------------------------------------


def test_telegram_cli_obis_v2():
    body_lines = [
        "/TEST",
        "1-0:1.8.1(002052.366*kWh)",
        "1-0:1.8.2(001898.022*kWh)",
    ]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(
            app, ["telegram", "--obis", "1-0:1.8.1", "--api-version", "v2"]
        )
    assert result.exit_code == 0
    assert "1-0:1.8.1(002052.366*kWh)" in result.output


def test_telegram_cli_obis_v1():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v1")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(
            app, ["telegram", "--obis", "1-0:1.8.1", "--api-version", "v1"]
        )
    assert result.exit_code == 0
    assert "1-0:1.8.1(002052.366*kWh)" in result.output


def test_telegram_cli_obis_not_found():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(
            app, ["telegram", "--obis", "1-0:9.9.9", "--api-version", "v2"]
        )
    assert result.exit_code == 0
    assert "OBIS code 1-0:9.9.9 not found" in result.output


# ---------------------------------------------------------------------------
# CLI --named / --format json
# ---------------------------------------------------------------------------


def test_telegram_cli_named_json():
    body_lines = [
        "/TEST",
        "1-0:1.8.1(002052.366*kWh)",
        "0-0:1.0.0(220815164518W)",
    ]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "telegram",
                "--format",
                "json",
                "--named",
                "--api-version",
                "v2",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "Total imported energy, tariff 1 (peak) — kWh" in parsed["obis"]
    assert "Timestamp of telegram" in parsed["obis"]


def test_telegram_cli_json_not_named():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(
            app, ["telegram", "--format", "json", "--api-version", "v2"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "1-0:1.8.1" in parsed["obis"]


def test_telegram_cli_named_unknown_obis():
    """Unknown OBIS codes fall back to the raw code as the key."""
    body_lines = ["/TEST", "9-9:9.9.9(12345)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "telegram",
                "--format",
                "json",
                "--named",
                "--api-version",
                "v2",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "9-9:9.9.9" in parsed["obis"]


# ---------------------------------------------------------------------------
# CLI --validate
# ---------------------------------------------------------------------------


def test_telegram_cli_validate_v2():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(app, ["telegram", "--validate", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "Valid" in result.output


def test_telegram_cli_validate_v2_invalid():
    raw = "/TEST\n1-0:1.8.1(002052.366*kWh)\n!0000"
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(app, ["telegram", "--validate", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "Invalid" in result.output


def test_telegram_cli_validate_v1():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v1")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(app, ["telegram", "--validate", "--api-version", "v1"])
    assert result.exit_code == 0
    assert "Valid" in result.output


# ---------------------------------------------------------------------------
# CLI raw output
# ---------------------------------------------------------------------------


def test_telegram_cli_raw_output():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")
    with patch("homewizard_cli.commands.telegram.resolve_client", return_value=client):
        result = runner.invoke(app, ["telegram", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "1-0:1.8.1(002052.366*kWh)" in result.output


# ---------------------------------------------------------------------------
# CLI --rate
# ---------------------------------------------------------------------------


def test_telegram_cli_rate():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")

    mock_times = [0.0, 30.0, 60.0, 90.0]
    time_idx = 0

    def mock_monotonic():
        nonlocal time_idx
        val = (
            mock_times[time_idx]
            if time_idx < len(mock_times)
            else mock_times[-1] + 30.0
        )
        time_idx += 1
        return val

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.telegram.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.telegram.time.monotonic",
            side_effect=mock_monotonic,
        ),
        patch(
            "homewizard_cli.commands.telegram.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _telegram_async(
                validate=False,
                obis=None,
                explain=None,
                named=False,
                watch=1.0,
                format="auto",
                rate=True,
                host="192.168.1.1",
                request_timeout=3.0,
                proxy=None,
                api_version="v2",
                token=None,
                no_verify=False,
            )
        )

    assert sleep_calls == 3


# ---------------------------------------------------------------------------
# CLI watch mode
# ---------------------------------------------------------------------------


def test_telegram_cli_watch_new_telegram():
    body_lines_1 = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    body_lines_2 = ["/TEST", "1-0:1.8.1(002052.367*kWh)"]
    raw1 = _make_valid_telegram(body_lines_1)
    raw2 = _make_valid_telegram(body_lines_2)

    call_count = 0

    async def mock_get(endpoint):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return raw1
        return raw2

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(side_effect=mock_get)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.telegram.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.telegram.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _telegram_async(
                validate=False,
                obis=None,
                explain=None,
                named=False,
                watch=1.0,
                format="auto",
                rate=False,
                host="192.168.1.1",
                request_timeout=3.0,
                proxy=None,
                api_version="v2",
                token=None,
                no_verify=False,
            )
        )

    assert call_count == 2
    assert sleep_calls == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_telegram_cli_fetch_error_watch():
    """Watch mode continues after a fetch error."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    async def mock_get(endpoint):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("fetch failed")
        return "/TEST\n!0000"

    client.get = AsyncMock(side_effect=mock_get)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.telegram.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.telegram.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _telegram_async(
                validate=False,
                obis=None,
                explain=None,
                named=False,
                watch=1.0,
                format="auto",
                rate=False,
                host="192.168.1.1",
                request_timeout=3.0,
                proxy=None,
                api_version="v2",
                token=None,
                no_verify=False,
            )
        )

    assert call_count == 2
    assert sleep_calls == 2


# ---------------------------------------------------------------------------
# Direct async unit tests
# ---------------------------------------------------------------------------


async def test_telegram_async_watch_obis_found():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 1:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.telegram.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.telegram.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        await _telegram_async(
            validate=False,
            obis="1-0:1.8.1",
            explain=None,
            named=False,
            watch=1.0,
            format="auto",
            rate=False,
            host="192.168.1.1",
            request_timeout=3.0,
            proxy=None,
            api_version="v2",
            token=None,
            no_verify=False,
        )

    assert sleep_calls == 1
    assert client.get.call_count == 1


async def test_telegram_async_watch_obis_not_found():
    body_lines = ["/TEST", "1-0:1.8.1(002052.366*kWh)"]
    raw = _make_valid_telegram(body_lines)
    client = _make_client_mock(raw, api_version="v2")

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 1:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.telegram.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.telegram.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        await _telegram_async(
            validate=False,
            obis="1-0:9.9.9",
            explain=None,
            named=False,
            watch=1.0,
            format="auto",
            rate=False,
            host="192.168.1.1",
            request_timeout=3.0,
            proxy=None,
            api_version="v2",
            token=None,
            no_verify=False,
        )

    assert sleep_calls == 1
    assert client.get.call_count == 1


# ---------------------------------------------------------------------------
# CRIT-2 regression: CRC includes the terminating '!' (DSMR spec)
# ---------------------------------------------------------------------------


def test_parse_telegram_crc_includes_bang():
    """A telegram whose CRC was computed over body+'!' must validate.

    DSMR spec + dsmr_parser reference compute the CRC over the content
    up to and INCLUDING the terminating '!' character.
    """
    body = "/TEST\n1-0:1.8.1(002052.366*kWh)\n0-0:1.0.0(220815164518W)\n"
    crc = _crc16((body + "!").encode("ascii"))
    raw = body + f"!{crc:04X}"
    result = _parse_telegram(raw)
    assert result["valid"] is True


def test_parse_telegram_real_device_format():
    """Real-device DSMR telegram format (CRLF endings, multi-group OBIS)."""
    body = (
        "/ISK5\\2M550E-1011\r\n"
        "\r\n"
        "1-3:0.2.8(50)\r\n"
        "0-0:1.0.0(260806172116S)\r\n"
        "0-0:96.1.1(4530303333303036373934323039373136)\r\n"
        "1-0:1.8.1(005321.207*kWh)\r\n"
        "0-1:24.2.1(260806172100S)(07256.089*m3)\r\n"
        "\r\n"
    )
    crc = _crc16((body + "!").encode("ascii"))
    raw = body + f"!{crc:04X}\r\n"
    result = _parse_telegram(raw)
    assert result["valid"] is True
    assert result["header"] == "/ISK5\\2M550E-1011"
    assert "0-1:24.2.1" in result["obis"]


def test_validate_and_print_crc_includes_bang():
    """--validate must accept telegrams whose CRC covers body+'!'."""
    body = "/TEST\n1-0:1.8.1(002052.366*kWh)\n"
    crc = _crc16((body + "!").encode("ascii"))
    raw = body + f"!{crc:04X}"
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    _validate_and_print(raw, console)
    assert "Valid" in buf.getvalue()


def test_raw_formatter_crc_includes_bang():
    """format/raw.py must emit a CRC that round-trips as valid."""
    from homewizard_cli.format.raw import write_raw
    from homewizard_cli.models import Measurement

    data = Measurement(
        meter_model="TEST",
        smr_version=50,
        unique_id="abc123",
        total_power_import_t1_kwh=2052.366,
        total_power_import_t2_kwh=1898.022,
        total_power_export_t1_kwh=0.0,
        total_power_export_t2_kwh=0.0,
        active_tariff=1,
        active_power_w=106.0,
    )
    buf = StringIO()
    console = Console(file=buf, force_terminal=False)
    write_raw(data, console)
    output = buf.getvalue().strip()
    body, crc = output.rsplit("!", 1)
    assert _crc16((body + "!").encode("ascii")) == int(crc, 16)
    # Round-trip: re-validating the emitted telegram must succeed
    check_buf = StringIO()
    _validate_and_print(output, Console(file=check_buf, force_terminal=True))
    assert "Valid" in check_buf.getvalue()
