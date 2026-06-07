"""Tests for cost command and cost calculator."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from homewizard_cli.commands.cost import _cost_async, _write_cost
from homewizard_cli.config import TariffConfig
from homewizard_cli.cost import CostCalculator
from homewizard_cli.main import app

runner = CliRunner()


# ── CostCalculator ─────────────────────────────────────────────


def test_calculate_basic():
    calc = CostCalculator(TariffConfig(t1_rate=0.30, export_credit=0.10))
    result = calc.calculate(
        {
            "total_power_import_kwh": 100.0,
            "total_power_export_kwh": 10.0,
            "active_tariff": 1,
        }
    )
    assert result["currency"] == "EUR"
    assert result["total_import_kwh"] == 100.0
    assert result["total_export_kwh"] == 10.0
    assert result["total_cost"] == 29.0  # 100*0.30 - 10*0.10


def test_calculate_with_tariffs():
    calc = CostCalculator(TariffConfig(t1_rate=0.30, t2_rate=0.20))
    result = calc.calculate(
        {
            "total_power_import_kwh": 100.0,
            "total_power_import_t1_kwh": 60.0,
            "total_power_import_t2_kwh": 40.0,
            "total_power_export_kwh": 0.0,
            "active_tariff": 1,
        }
    )
    assert result["t1_cost"] == 18.0
    assert result["t2_cost"] == 8.0
    assert result["total_cost"] == 26.0


def test_calculate_history():
    calc = CostCalculator(TariffConfig(t1_rate=0.30, export_credit=0.10))
    rows = [
        {"total_power_import_kwh": 100.0, "total_power_export_kwh": 10.0},
        {"total_power_import_kwh": 110.0, "total_power_export_kwh": 15.0},
    ]
    result = calc.calculate_history(rows)
    assert result["period_import_kwh"] == 10.0
    assert result["period_export_kwh"] == 5.0
    assert result["period_cost"] == 2.5  # 10*0.30 - 5*0.10


def test_calculate_history_empty():
    calc = CostCalculator(TariffConfig())
    result = calc.calculate_history([])
    assert result["period_cost"] == 0.0


# ── CLI ────────────────────────────────────────────────────────


def test_cost_help():
    result = runner.invoke(app, ["cost", "--help"])
    assert result.exit_code == 0
    assert "cost" in result.output.lower()


def test_cost_realtime():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(
        return_value=AsyncMock(
            model_dump=lambda: {
                "total_power_import_kwh": 100.0,
                "total_power_export_kwh": 10.0,
                "active_tariff": 1,
            }
        )
    )

    with patch("homewizard_cli.commands.cost.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "cost",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--format",
                "json",
            ],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_cost"] == 29.0


def test_cost_tariffs():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(
        return_value=AsyncMock(
            model_dump=lambda: {
                "total_power_import_kwh": 100.0,
                "total_power_import_t1_kwh": 60.0,
                "total_power_import_t2_kwh": 40.0,
                "total_power_export_kwh": 0.0,
                "active_tariff": 1,
            }
        )
    )

    with patch("homewizard_cli.commands.cost.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "cost",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--tariffs",
            ],
        )
    assert result.exit_code == 0
    assert "T1" in result.output
    assert "T2" in result.output


def test_cost_custom_rates():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(
        return_value=AsyncMock(
            model_dump=lambda: {
                "total_power_import_kwh": 100.0,
                "total_power_export_kwh": 0.0,
                "active_tariff": 1,
            }
        )
    )

    with patch("homewizard_cli.commands.cost.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "cost",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--format",
                "json",
                "--t1-rate",
                "0.50",
            ],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["t1_rate"] == 0.50
    assert data["total_cost"] == 50.0


# ── _write_cost ────────────────────────────────────────────────


def test_write_cost_json():
    from homewizard_cli.format import Format

    console = MagicMock()
    console.print = MagicMock()
    _write_cost({"total_cost": 10.0, "currency": "EUR"}, Format.JSON, console, False)
    printed = console.print.call_args[0][0]
    assert "10.0" in printed


def test_write_cost_table():
    from homewizard_cli.format import Format
    from rich.table import Table

    console = MagicMock()
    console.print = MagicMock()
    _write_cost(
        {
            "total_cost": 29.0,
            "currency": "EUR",
            "t1_import_kwh": 100.0,
            "t1_rate": 0.30,
            "t1_cost": 30.0,
            "total_export_kwh": 10.0,
            "export_credit": 1.0,
        },
        Format.TABLE,
        console,
        True,
    )
    printed = console.print.call_args[0][0]
    assert isinstance(printed, Table)
    assert printed.row_count > 0


def test_cost_async_no_db():
    """Test that _cost_async works without DB when not in history mode."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(
        return_value=AsyncMock(
            model_dump=lambda: {
                "total_power_import_kwh": 50.0,
                "total_power_export_kwh": 0.0,
                "active_tariff": 1,
            }
        )
    )

    with patch("homewizard_cli.commands.cost.resolve_client", return_value=client):
        asyncio.run(
            _cost_async(
                host="192.168.1.1",
                timeout=3.0,
                api_version="v2",
                token=None,
                no_verify=False,
                proxy=None,
                format="json",
                watch=None,
                today=False,
                yesterday=False,
                this_month=False,
                tariffs=False,
                db=None,
                t1_rate=None,
                t2_rate=None,
                t3_rate=None,
                t4_rate=None,
                export_credit=None,
                currency=None,
            )
        )


def test_cost_history_today():
    """Test cost --today reads from SQLite DB."""
    import tempfile

    from homewizard_cli.storage import MeasurementStore

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = MeasurementStore(db_path)
    store.append(
        {
            "total_power_import_kwh": 100.0,
            "total_power_export_kwh": 10.0,
            "active_tariff": 1,
        },
        "ABC123",
    )
    store.append(
        {
            "total_power_import_kwh": 110.0,
            "total_power_export_kwh": 15.0,
            "active_tariff": 1,
        },
        "ABC123",
    )
    store.close()

    result = runner.invoke(
        app,
        [
            "cost",
            "--today",
            "--db",
            db_path,
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["period_cost"] == 2.5
    import os

    os.unlink(db_path)


def test_cost_history_yesterday():
    """Test cost --yesterday with no rows returns 0."""
    import tempfile

    from homewizard_cli.storage import MeasurementStore

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = MeasurementStore(db_path)
    # Insert old row (more than 1 day ago)
    store.append(
        {
            "total_power_import_kwh": 50.0,
            "total_power_export_kwh": 0.0,
            "active_tariff": 1,
        },
        "ABC123",
    )
    store.close()

    result = runner.invoke(
        app,
        [
            "cost",
            "--yesterday",
            "--db",
            db_path,
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["period_cost"] == 0.0
    import os

    os.unlink(db_path)


def test_cost_watch_mode():
    """Test cost --watch polls at least once."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    call_count = 0

    async def mock_get_json_v2(path, model):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise RuntimeError("stop")
        return AsyncMock(
            model_dump=lambda: {
                "total_power_import_kwh": 100.0,
                "total_power_export_kwh": 0.0,
                "active_tariff": 1,
            }
        )

    client.get_json_v2 = mock_get_json_v2

    with patch("homewizard_cli.commands.cost.resolve_client", return_value=client):
        with patch(
            "homewizard_cli.commands.cost.asyncio.sleep",
            side_effect=RuntimeError("stop"),
        ):
            with pytest.raises(RuntimeError, match="stop"):
                asyncio.run(
                    _cost_async(
                        host="192.168.1.1",
                        timeout=3.0,
                        api_version="v2",
                        token=None,
                        no_verify=False,
                        proxy=None,
                        format="json",
                        watch=0.01,
                        today=False,
                        yesterday=False,
                        this_month=False,
                        tariffs=False,
                        db=None,
                        t1_rate=None,
                        t2_rate=None,
                        t3_rate=None,
                        t4_rate=None,
                        export_credit=None,
                        currency=None,
                    )
                )
    assert call_count == 1


def test_cost_custom_currency():
    """Test cost --currency overrides default."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(
        return_value=AsyncMock(
            model_dump=lambda: {
                "total_power_import_kwh": 100.0,
                "total_power_export_kwh": 0.0,
                "active_tariff": 1,
            }
        )
    )

    with patch("homewizard_cli.commands.cost.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "cost",
                "--api-version",
                "v2",
                "--host",
                "192.168.1.1",
                "--format",
                "json",
                "--currency",
                "USD",
            ],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["currency"] == "USD"
