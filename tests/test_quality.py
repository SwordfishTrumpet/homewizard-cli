# tests/test_quality.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from homewizard_cli.commands.quality import (
    _parse_events_from_telegram,
    _quality_async,
    _type_name,
)
from homewizard_cli.main import app
from homewizard_cli.models import Measurement
from homewizard_cli.models.v2 import TelegramV2

runner = CliRunner()


def _make_client_mock(measurement: Measurement, telegram: str | None = None):
    """Create a mock client for quality tests."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    async def mock_get_json_v2(endpoint, model):
        if endpoint == "/api/measurement":
            return measurement
        elif endpoint == "/api/telegram":
            if telegram is not None:
                return TelegramV2(telegram=telegram)
            raise Exception("no telegram mock")
        raise Exception(f"unexpected endpoint: {endpoint}")

    client.get_json_v2 = AsyncMock(side_effect=mock_get_json_v2)
    return client


# ---------------------------------------------------------------------------
# _type_name
# ---------------------------------------------------------------------------


def test_type_name():
    assert _type_name("0-0:96.7.19") == "Short outage"
    assert _type_name("0-0:96.7.9") == "Long outage"
    assert _type_name("0-0:96.7.21") == "Unknown"
    assert _type_name("abc") == "Unknown"


# ---------------------------------------------------------------------------
# _parse_events_from_telegram
# ---------------------------------------------------------------------------


def test_parse_events_normal_no_obis():
    raw = "/TEST\n1-0:1.8.1(002052.366*kWh)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


def test_parse_events_normal_count_zero():
    raw = "/TEST\n1-0:99.97.0(0)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


def test_parse_events_short_outage():
    raw = (
        "/TEST\n"
        "1-0:99.97.0(2)"
        "(0-0:96.7.19)"
        "(220815164518W)"
        "(0000000229*s)"
        "(220815164518W)"
        "(0000000229*s)\n"
        "!1234"
    )
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert len(events) == 2
    assert events[0]["type"] == "Short outage"
    assert events[0]["duration"] == "229"
    assert events[1]["type"] == "Short outage"
    assert events[1]["duration"] == "229"


def test_parse_events_long_outage():
    raw = "/TEST\n1-0:99.97.0(1)(0-0:96.7.9)(220815164518W)(0000000456*s)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert len(events) == 1
    assert events[0]["type"] == "Long outage"
    assert events[0]["duration"] == "456"


def test_parse_events_mixed():
    raw = (
        "/TEST\n"
        "1-0:99.97.0(2)"
        "(0-0:96.7.19)"
        "(220815164518W)"
        "(0000000229*s)"
        "(0-0:96.7.9)"
        "(220815164518W)"
        "(0000000456*s)\n"
        "!1234"
    )
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert len(events) == 2
    assert events[0]["type"] == "Short outage"
    assert events[1]["type"] == "Long outage"


def test_parse_events_malformed():
    raw = "/TEST\n1-0:99.97.0(1)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


def test_parse_events_invalid_count():
    raw = "/TEST\n1-0:99.97.0(abc)(0-0:96.7.19)(220815164518W)(0000000229*s)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


def test_parse_events_timestamp_formatting():
    raw = "/TEST\n1-0:99.97.0(1)(0-0:96.7.19)(220815164518W)(0000000229*s)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format="%d/%m/%Y %H:%M"),
    ):
        events = _parse_events_from_telegram(raw)
    assert events[0]["timestamp"] == "15/08/2022 16:45"


def test_parse_events_invalid_timestamp():
    raw = "/TEST\n1-0:99.97.0(1)(0-0:96.7.19)(badtsW)(0000000229*s)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events[0]["timestamp"] == "badts"


def test_parse_events_empty_duration():
    raw = "/TEST\n1-0:99.97.0(1)(0-0:96.7.19)(220815164518W)(noseconds)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events[0]["duration"] == ""


def test_parse_events_long_outage_no_duration():
    """When no duration part exists, the event is skipped (code breaks early)."""
    raw = "/TEST\n1-0:99.97.0(1)(0-0:96.7.9)(220815164518W)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


def test_parse_events_count_exceeds_actual():
    """Count claims 5 events but only 1 is present."""
    raw = "/TEST\n1-0:99.97.0(5)(0-0:96.7.19)(220815164518W)(0000000229*s)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert len(events) == 1
    assert events[0]["type"] == "Short outage"
    assert events[0]["duration"] == "229"


def test_parse_events_missing_timestamp():
    """Count=1 with type but no timestamp/duration parts."""
    raw = "/TEST\n1-0:99.97.0(1)(0-0:96.7.19)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


def test_parse_events_type_without_count_prefix():
    """Type field exists but count part is invalid (not numeric)."""
    raw = "/TEST\n1-0:99.97.0(0)(abc)(badtsW)(nodur)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


def test_parse_events_only_obis_line_no_parts():
    """OBIS line present but only the count, no event parts."""
    raw = "/TEST\n1-0:99.97.0(0)\n!1234"
    with patch(
        "homewizard_cli.commands.quality.load_config",
        return_value=MagicMock(timestamp_format=None),
    ):
        events = _parse_events_from_telegram(raw)
    assert events == [{"type": "normal", "timestamp": "", "duration": ""}]


# ---------------------------------------------------------------------------
# CLI one-shot
# ---------------------------------------------------------------------------


def test_quality_cli_v2_oneshot():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        voltage_sag_l2_count=2,
        voltage_swell_l2_count=1,
        voltage_sag_l3_count=1,
        voltage_swell_l3_count=0,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = _make_client_mock(measurement)
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "Voltage Sags L1: 3" in result.output
    assert "Voltage Swells L1: 1" in result.output
    assert "Voltage Sags L2: 2" in result.output
    assert "Voltage Swells L2: 1" in result.output
    assert "Voltage Sags L3: 1" in result.output
    assert "Voltage Swells L3: 0" in result.output
    assert "Short Failures:  5" in result.output
    assert "Long Failures:   2" in result.output


def test_quality_cli_v2_l1_only():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = _make_client_mock(measurement)
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "Voltage Sags L1: 3" in result.output
    assert "Voltage Swells L1: 1" in result.output
    assert "Voltage Sags L2" not in result.output
    assert "Voltage Swells L2" not in result.output
    assert "Voltage Sags L3" not in result.output
    assert "Voltage Swells L3" not in result.output


def test_quality_cli_v1_oneshot():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json = AsyncMock(return_value=measurement)
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--api-version", "v1"])
    assert result.exit_code == 0
    assert "Voltage Sags L1: 3" in result.output


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------


def test_quality_cli_alert_same_counts_oneshot():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = _make_client_mock(measurement)
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--alert", "--api-version", "v2"])
    assert result.exit_code == 0
    # One-shot prints on first call because previous is None
    assert "Voltage Sags L1: 3" in result.output
    assert client.get_json_v2.call_count == 1


def test_quality_cli_alert_same_counts_watch():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = _make_client_mock(measurement)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.quality.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.quality.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _quality_async(
                watch=0.1,
                alert=True,
                show_events=False,
                host="192.168.1.1",
                request_timeout=3.0,
                proxy=None,
                api_version="v2",
                token=None,
                no_verify=False,
            )
        )

    assert sleep_calls == 2
    assert client.get_json_v2.call_count == 2


def test_quality_cli_alert_different_counts():
    measurement1 = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    measurement2 = Measurement(
        voltage_sag_l1_count=4,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )

    call_count = 0

    async def mock_get(endpoint, model):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return measurement1
        return measurement2

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(side_effect=mock_get)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.quality.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.quality.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        asyncio.run(
            _quality_async(
                watch=0.1,
                alert=True,
                show_events=False,
                host="192.168.1.1",
                request_timeout=3.0,
                proxy=None,
                api_version="v2",
                token=None,
                no_verify=False,
            )
        )

    assert sleep_calls == 2
    assert call_count == 2


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def test_quality_cli_events_normal():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    telegram = "/TEST\n1-0:1.8.1(002052.366*kWh)\n!1234"
    client = _make_client_mock(measurement, telegram=telegram)
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--events", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "Power Failure Events: None" in result.output


def test_quality_cli_events_with_outages():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    telegram = "/TEST\n1-0:99.97.0(1)(0-0:96.7.19)(220815164518W)(0000000229*s)\n!1234"
    client = _make_client_mock(measurement, telegram=telegram)
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--events", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "Power Failure Events:" in result.output
    assert "Short outage" in result.output
    assert "229" in result.output


def test_quality_cli_events_v1():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    telegram = "/TEST\n1-0:99.97.0(1)(0-0:96.7.19)(220815164518W)(0000000229*s)\n!1234"
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json = AsyncMock(return_value=measurement)
    client.get = AsyncMock(return_value=telegram)
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--events", "--api-version", "v1"])
    assert result.exit_code == 0
    assert "Short outage" in result.output


def test_quality_cli_events_fetch_error():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(
        side_effect=lambda endpoint, model: (
            measurement
            if endpoint == "/api/measurement"
            else (_ for _ in ()).throw(RuntimeError("telegram fail"))
        )
    )
    with patch("homewizard_cli.commands.quality.resolve_client", return_value=client):
        result = runner.invoke(app, ["quality", "--events", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "could not fetch event log" in result.output


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------


def test_quality_cli_watch_warning():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = _make_client_mock(measurement)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 1:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.quality.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.quality.asyncio.sleep",
            side_effect=mock_sleep,
        ),
    ):
        result = runner.invoke(
            app, ["quality", "--watch", "0.5", "--api-version", "v2"]
        )

    assert "Warning" in result.output
    assert "0.5s" in result.output


# ---------------------------------------------------------------------------
# Direct async watch with all phases
# ---------------------------------------------------------------------------


async def test_quality_async_watch_all_phases():
    measurement = Measurement(
        voltage_sag_l1_count=3,
        voltage_swell_l1_count=1,
        voltage_sag_l2_count=2,
        voltage_swell_l2_count=1,
        voltage_sag_l3_count=1,
        voltage_swell_l3_count=0,
        any_power_fail_count=5,
        long_power_fail_count=2,
    )
    client = _make_client_mock(measurement)

    sleep_calls = 0

    async def mock_sleep(val):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 1:
            raise RuntimeError("stop")

    with (
        patch("homewizard_cli.commands.quality.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.quality.asyncio.sleep",
            side_effect=mock_sleep,
        ),
        pytest.raises(RuntimeError, match="stop"),
    ):
        await _quality_async(
            watch=0.1,
            alert=False,
            show_events=False,
            host="192.168.1.1",
            request_timeout=3.0,
            proxy=None,
            api_version="v2",
            token=None,
            no_verify=False,
        )

    assert sleep_calls == 1
    assert client.get_json_v2.call_count == 1
