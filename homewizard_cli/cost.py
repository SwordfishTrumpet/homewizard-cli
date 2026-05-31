"""Cost calculation for energy consumption."""

from typing import Any

from .config import TariffConfig


def _get_tariff_rate(tariff: int, config: TariffConfig) -> float:
    """Return rate for a given tariff number."""
    return {
        1: config.t1_rate,
        2: config.t2_rate,
        3: config.t3_rate,
        4: config.t4_rate,
    }.get(tariff, config.t1_rate)


def _safe_float(value: Any) -> float:
    """Coerce value to float, defaulting to 0.0."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


class CostCalculator:
    """Calculate energy costs from meter readings."""

    def __init__(self, config: TariffConfig) -> None:
        self.config = config

    def calculate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Calculate cost breakdown from a single Measurement dict.

        Returns dict with tariff breakdowns, total cost, and currency.
        """
        cfg = self.config

        total_import = _safe_float(data.get("total_power_import_kwh"))
        total_export = _safe_float(data.get("total_power_export_kwh"))
        active_tariff = int(data.get("active_tariff", 1) or 1)

        # Tariff-specific import
        t1_import = _safe_float(data.get("total_power_import_t1_kwh"))
        t2_import = _safe_float(data.get("total_power_import_t2_kwh"))
        t3_import = _safe_float(data.get("total_power_import_t3_kwh"))
        t4_import = _safe_float(data.get("total_power_import_t4_kwh"))

        # If tariff-specific totals are missing, fall back to total * rate
        if t1_import == 0 and t2_import == 0 and active_tariff == 1:
            t1_import = total_import
        if t1_import == 0 and t2_import == 0 and t3_import == 0 and t4_import == 0:
            t1_import = total_import

        t1_cost = t1_import * cfg.t1_rate
        t2_cost = t2_import * cfg.t2_rate
        t3_cost = t3_import * cfg.t3_rate
        t4_cost = t4_import * cfg.t4_rate

        export_credit = total_export * cfg.export_credit
        total_cost = t1_cost + t2_cost + t3_cost + t4_cost - export_credit

        return {
            "currency": cfg.currency,
            "t1_import_kwh": round(t1_import, 3),
            "t1_rate": cfg.t1_rate,
            "t1_cost": round(t1_cost, 2),
            "t2_import_kwh": round(t2_import, 3),
            "t2_rate": cfg.t2_rate,
            "t2_cost": round(t2_cost, 2),
            "t3_import_kwh": round(t3_import, 3),
            "t3_rate": cfg.t3_rate,
            "t3_cost": round(t3_cost, 2),
            "t4_import_kwh": round(t4_import, 3),
            "t4_rate": cfg.t4_rate,
            "t4_cost": round(t4_cost, 2),
            "total_import_kwh": round(total_import, 3),
            "total_export_kwh": round(total_export, 3),
            "export_credit": round(export_credit, 2),
            "total_cost": round(total_cost, 2),
        }

    def calculate_history(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate cost from a list of historical rows.

        Uses the first row as the baseline and computes delta cost
        for the period covered by the rows.
        """
        if not rows:
            return {
                "currency": self.config.currency,
                "period_cost": 0.0,
                "total_cost": 0.0,
            }

        first = rows[0]
        last = rows[-1]

        first_import = _safe_float(first.get("total_power_import_kwh"))
        last_import = _safe_float(last.get("total_power_import_kwh"))
        first_export = _safe_float(first.get("total_power_export_kwh"))
        last_export = _safe_float(last.get("total_power_export_kwh"))

        period_import = max(0.0, last_import - first_import)
        period_export = max(0.0, last_export - first_export)

        # Use active tariff from last row for rate selection
        active_tariff = int(last.get("active_tariff", 1) or 1)
        rate = _get_tariff_rate(active_tariff, self.config)

        period_cost = period_import * rate - period_export * self.config.export_credit

        return {
            "currency": self.config.currency,
            "period_import_kwh": round(period_import, 3),
            "period_export_kwh": round(period_export, 3),
            "period_cost": round(period_cost, 2),
            "total_cost": round(period_cost, 2),
        }
