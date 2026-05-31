import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from homewizard_cli.alerting import AlertDispatcher
from homewizard_cli.main import app
from homewizard_cli.models import DataResponse

runner = CliRunner()


class TestAlertDispatcher:
    def test_configured_false_by_default(self):
        d = AlertDispatcher()
        assert d.configured is False

    def test_configured_with_webhook(self):
        d = AlertDispatcher(webhook_urls=["https://example.com/hook"])
        assert d.configured is True

    def test_configured_with_command(self):
        d = AlertDispatcher(commands=["echo hello"])
        assert d.configured is True

    def test_should_fire_no_cooldown(self):
        d = AlertDispatcher(cooldown_seconds=0.0)
        assert d._should_fire() is False  # not configured
        d = AlertDispatcher(
            webhook_urls=["https://example.com/hook"], cooldown_seconds=0.0
        )
        assert d._should_fire() is True

    def test_cooldown_blocks_rapid_fire(self):
        d = AlertDispatcher(
            webhook_urls=["https://example.com/hook"], cooldown_seconds=60.0
        )
        assert d._should_fire() is True
        d._mark_fired()
        assert d._should_fire() is False

    def test_cooldown_expires(self):
        d = AlertDispatcher(
            webhook_urls=["https://example.com/hook"], cooldown_seconds=0.001
        )
        d._mark_fired()
        time.sleep(0.002)
        assert d._should_fire() is True

    @pytest.mark.asyncio
    async def test_dispatch_noop_when_not_configured(self):
        d = AlertDispatcher()
        await d.dispatch("test > 1", {"test": 2})

    @pytest.mark.asyncio
    async def test_dispatch_posts_webhook(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_client):
            d = AlertDispatcher(
                webhook_urls=["https://hooks.example.com/test"], cooldown_seconds=0.0
            )
            await d.dispatch("active_power_w > 1000", {"active_power_w": 1500.0})

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.example.com/test"
        payload = call_args[1]["json"]
        assert payload["condition"] == "active_power_w > 1000"
        assert payload["data"]["active_power_w"] == 1500.0

    @pytest.mark.asyncio
    async def test_dispatch_runs_command(self):
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock()

        with patch(
            "asyncio.create_subprocess_shell", return_value=mock_proc
        ) as mock_sp:
            d = AlertDispatcher(commands=["echo test"], cooldown_seconds=0.0)
            await d.dispatch("test > 1", {"test": 2})

        mock_sp.assert_called_once()
        call_args = mock_sp.call_args[0]
        assert call_args[0] == "echo test"
        assert mock_sp.call_args[1]["env"]["HW_CONDITION"] == "test > 1"

    @pytest.mark.asyncio
    async def test_dispatch_cooldown_skips(self):
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock()

        with patch(
            "asyncio.create_subprocess_shell", return_value=mock_proc
        ) as mock_sp:
            d = AlertDispatcher(commands=["echo one"], cooldown_seconds=10.0)
            await d.dispatch("test > 1", {"test": 2})
            assert mock_sp.call_count == 1
            await d.dispatch("test > 1", {"test": 3})
            assert mock_sp.call_count == 1  # blocked by cooldown

    @pytest.mark.asyncio
    async def test_dispatch_handles_exceptions(self):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.side_effect = httpx.ConnectError("connection refused")
            d = AlertDispatcher(
                webhook_urls=["https://broken.example.com"], cooldown_seconds=0.0
            )
            await d.dispatch("test > 1", {"test": 2})

    @pytest.mark.asyncio
    async def test_dispatch_both_webhook_and_command_fail(self):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("webhook fail"))

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch(
                "asyncio.create_subprocess_shell",
                side_effect=RuntimeError("subprocess fail"),
            ),
        ):
            d = AlertDispatcher(
                webhook_urls=["https://hook.example.com"],
                commands=["echo test"],
                cooldown_seconds=0.0,
            )
            await d.dispatch("test > 1", {"test": 2})


class TestDataAlertIntegration:
    def test_data_help_shows_alert_options(self):
        result = runner.invoke(app, ["data", "--help"])
        assert result.exit_code == 0
        assert "--alert-webhook" in result.output
        assert "--alert-cmd" in result.output
        assert "--alert-cooldown" in result.output

    def test_data_until_with_alert_webhook_exits_10(self):
        with patch("homewizard_cli.commands.data.resolve_client") as mock_resolve:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.get_json = AsyncMock(
                return_value=DataResponse(
                    wifi_ssid="Test",
                    wifi_strength=100,
                    smr_version=50,
                    meter_model="TEST",
                    unique_id="abc",
                    active_tariff=1,
                    total_power_import_kwh=100.0,
                    total_power_import_t1_kwh=50.0,
                    total_power_import_t2_kwh=50.0,
                    total_power_export_kwh=0.0,
                    total_power_export_t1_kwh=0.0,
                    total_power_export_t2_kwh=0.0,
                    active_power_w=1500.0,
                )
            )
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                [
                    "data",
                    "--api-version",
                    "v1",
                    "--until",
                    "active_power_w > 1000",
                    "--alert-webhook",
                    "https://hooks.example.com/test",
                ],
            )
            assert result.exit_code == 10
            assert "Condition met" in result.output

    def test_data_watch_until_no_alert_exits_10(self):
        with patch("homewizard_cli.commands.data.resolve_client") as mock_resolve:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.get_json = AsyncMock(
                return_value=DataResponse(
                    wifi_ssid="Test",
                    wifi_strength=100,
                    smr_version=50,
                    meter_model="TEST",
                    unique_id="abc",
                    active_tariff=1,
                    total_power_import_kwh=100.0,
                    total_power_import_t1_kwh=50.0,
                    total_power_import_t2_kwh=50.0,
                    total_power_export_kwh=0.0,
                    total_power_export_t1_kwh=0.0,
                    total_power_export_t2_kwh=0.0,
                    active_power_w=1500.0,
                )
            )
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                [
                    "data",
                    "--api-version",
                    "v1",
                    "--watch",
                    "2",
                    "--until",
                    "active_power_w > 1000",
                ],
            )
            assert result.exit_code == 10


class TestPowerAlertIntegration:
    def test_power_help_shows_alert_options(self):
        result = runner.invoke(app, ["power", "--help"])
        assert result.exit_code == 0
        assert "--alert-webhook" in result.output
        assert "--alert-cmd" in result.output
        assert "--alert-cooldown" in result.output

    def test_power_until_with_alert_webhook_exits_10(self):
        with patch("homewizard_cli.commands.power.resolve_client") as mock_resolve:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.get_json = AsyncMock(
                return_value=DataResponse(
                    wifi_ssid="Test",
                    wifi_strength=100,
                    smr_version=50,
                    meter_model="TEST",
                    unique_id="abc",
                    active_tariff=1,
                    total_power_import_kwh=100.0,
                    total_power_import_t1_kwh=50.0,
                    total_power_import_t2_kwh=50.0,
                    total_power_export_kwh=0.0,
                    total_power_export_t1_kwh=0.0,
                    total_power_export_t2_kwh=0.0,
                    active_power_w=1500.0,
                )
            )
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                [
                    "power",
                    "--api-version",
                    "v1",
                    "--until",
                    "active_power_w > 1000",
                    "--alert-webhook",
                    "https://hooks.example.com/test",
                ],
            )
            assert result.exit_code == 10


class TestExportAlertIntegration:
    def test_export_help_shows_alert_options(self):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        assert "--alert-webhook" in result.output
        assert "--alert-cmd" in result.output
        assert "--alert-cooldown" in result.output
