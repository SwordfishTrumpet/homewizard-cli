# tests/test_dashboard.py
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from homewizard_cli.models import Measurement

runner = CliRunner()


def _render_to_str(renderable: Any) -> str:
    """Render a Rich object to plain string for assertions."""
    console = Console(force_terminal=True, width=80)
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()


# ---------------------------------------------------------------------------
# Sparkline tests
# ---------------------------------------------------------------------------


def test_render_sparkline_empty():
    from homewizard_cli.commands.dashboard import _render_sparkline

    assert _render_sparkline([]) == ""


def test_render_sparkline_single():
    from homewizard_cli.commands.dashboard import _render_sparkline

    result = _render_sparkline([5.0])
    assert len(result) == 1
    assert result in {"▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"}


def test_render_sparkline_multi():
    from homewizard_cli.commands.dashboard import _render_sparkline

    result = _render_sparkline([0.0, 4.0, 8.0])
    assert len(result) == 3
    # 0.0 → min → first char, 8.0 → max → last char
    assert result[0] == "▁"
    assert result[2] == "█"


# ---------------------------------------------------------------------------
# _make_power_table tests
# ---------------------------------------------------------------------------


def test_make_power_table_importing():
    from homewizard_cli.commands.dashboard import _make_power_table

    data = Measurement(active_power_w=500.0)
    table = _make_power_table(data)
    output = _render_to_str(table)
    assert "importing" in output
    assert "500" in output


def test_make_power_table_exporting():
    from homewizard_cli.commands.dashboard import _make_power_table

    data = Measurement(active_power_w=-300.0)
    table = _make_power_table(data)
    output = _render_to_str(table)
    assert "exporting" in output
    assert "-300" in output


def test_make_power_table_with_l1():
    from homewizard_cli.commands.dashboard import _make_power_table

    data = Measurement(
        active_power_w=500.0,
        active_power_l1_w=200.0,
        active_voltage_l1_v=239.5,
        active_current_l1_a=0.5,
    )
    table = _make_power_table(data)
    output = _render_to_str(table)
    assert "L1" in output
    assert "239.5" in output
    assert "0.5" in output


# ---------------------------------------------------------------------------
# _make_energy_table tests
# ---------------------------------------------------------------------------


def test_make_energy_table():
    from homewizard_cli.commands.dashboard import _make_energy_table

    data = Measurement(
        total_power_import_kwh=100.0,
        total_power_export_kwh=25.0,
    )
    table = _make_energy_table(data)
    output = _render_to_str(table)
    assert "100.00" in output
    assert "25.00" in output
    # Net = 100 - 25 = 75
    assert "75.00" in output


# ---------------------------------------------------------------------------
# _make_gas_panel tests
# ---------------------------------------------------------------------------


def test_make_gas_panel_with_gas():
    from homewizard_cli.commands.dashboard import _make_gas_panel

    data = Measurement(total_gas_m3=1234.56)
    panel = _make_gas_panel(data)
    output = _render_to_str(panel)
    # 1234.56 is formatted as 1,234.56 with thousands separator
    assert "1,234.56" in output
    assert "m³" in output


def test_make_gas_panel_without_gas():
    from homewizard_cli.commands.dashboard import _make_gas_panel

    data = Measurement(total_gas_m3=None)
    panel = _make_gas_panel(data)
    output = _render_to_str(panel)
    assert "No gas meter" in output


# ---------------------------------------------------------------------------
# CLI help
# ---------------------------------------------------------------------------


def test_dashboard_help():
    from homewizard_cli.main import app

    result = runner.invoke(app, ["dashboard", "--help"])
    assert result.exit_code == 0
    assert "dashboard" in result.output.lower()


# ---------------------------------------------------------------------------
# _dashboard_async one-shot test
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dashboard_async_one_shot():
    from homewizard_cli.commands.dashboard import _dashboard_async

    with patch(
        "homewizard_cli.commands.dashboard.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            return_value=Measurement(
                active_power_w=500.0,
                meter_model="TEST",
                wifi_ssid="TestNet",
                wifi_strength=80,
                total_power_import_kwh=100.0,
                total_power_export_kwh=10.0,
                total_gas_m3=50.0,
            )
        )

        with patch("homewizard_cli.commands.dashboard.Live") as mock_live:
            mock_live.return_value.__enter__ = MagicMock(return_value=None)
            mock_live.return_value.__exit__ = MagicMock(return_value=None)

            with patch("homewizard_cli.commands.dashboard.asyncio.sleep") as mock_sleep:
                mock_sleep.side_effect = [asyncio.CancelledError()]

                await _dashboard_async(
                    watch=2.0,
                    host="192.168.1.100",
                    request_timeout=3.0,
                    api_version="v2",
                )

        client.get_json_v2.assert_awaited_once()
        mock_live.assert_called_once()


@pytest.mark.anyio
async def test_dashboard_async_v1():
    from homewizard_cli.commands.dashboard import _dashboard_async

    with patch(
        "homewizard_cli.commands.dashboard.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json = AsyncMock(
            return_value=Measurement(
                active_power_w=300.0,
                meter_model="TEST",
                wifi_ssid="TestNet",
                wifi_strength=80,
                total_power_import_kwh=50.0,
                total_power_export_kwh=5.0,
                total_gas_m3=None,
            )
        )

        with patch("homewizard_cli.commands.dashboard.Live") as mock_live:
            mock_live.return_value.__enter__ = MagicMock(return_value=None)
            mock_live.return_value.__exit__ = MagicMock(return_value=None)

            with patch("homewizard_cli.commands.dashboard.asyncio.sleep") as mock_sleep:
                mock_sleep.side_effect = [asyncio.CancelledError()]

                await _dashboard_async(
                    watch=2.0,
                    host="192.168.1.100",
                    request_timeout=3.0,
                    api_version="v1",
                )

        client.get_json.assert_awaited_once()


@pytest.mark.anyio
async def test_dashboard_async_keyboard_interrupt():
    from homewizard_cli.commands.dashboard import _dashboard_async

    with patch(
        "homewizard_cli.commands.dashboard.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            return_value=Measurement(
                active_power_w=500.0,
                meter_model="TEST",
                wifi_ssid="TestNet",
                wifi_strength=80,
                total_power_import_kwh=100.0,
                total_power_export_kwh=10.0,
                total_gas_m3=50.0,
            )
        )

        with patch("homewizard_cli.commands.dashboard.Live") as mock_live:
            mock_live.return_value.__enter__ = MagicMock(return_value=None)
            mock_live.return_value.__exit__ = MagicMock(return_value=None)

            with patch("homewizard_cli.commands.dashboard.asyncio.sleep") as mock_sleep:
                mock_sleep.side_effect = KeyboardInterrupt()

                await _dashboard_async(
                    watch=2.0,
                    host="192.168.1.100",
                    request_timeout=3.0,
                    api_version="v2",
                )

        client.get_json_v2.assert_awaited_once()
