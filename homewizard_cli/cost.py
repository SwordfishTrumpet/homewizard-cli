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
        return float(value)
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
        tariff_import = {
            1: _safe_float(data.get("total_power_import_t1_kwh")),
            2: _safe_float(data.get("total_power_import_t2_kwh")),
            3: _safe_float(data.get("total_power_import_t3_kwh")),
            4: _safe_float(data.get("total_power_import_t4_kwh")),
        }

        # Only a reading with no tariff counter at all falls back to the total.
        # Charging the total to T1 next to a real T3/T4 counter billed the same
        # energy twice, and total-only readings were billed at T1 even while
        # another tariff was active (#24).
        if not any(tariff_import.values()):
            fallback = active_tariff if active_tariff in tariff_import else 1
            tariff_import[fallback] = total_import

        t1_import = tariff_import[1]
        t2_import = tariff_import[2]
        t3_import = tariff_import[3]
        t4_import = tariff_import[4]

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

        Uses the first row as the baseline and sums each tariff's own counter
        delta, so a period that used peak and off-peak energy is billed per
        tariff instead of at whichever tariff the last row happened to carry
        (#25). Rows without any tariff counter fall back to the total delta at
        the last row's tariff.
        """
        empty = {
            "currency": self.config.currency,
            "period_cost": 0.0,
            "total_cost": 0.0,
        }
        empty.update({f"t{i}_import_kwh": 0.0 for i in range(1, 5)})
        empty.update({f"t{i}_rate": 0.0 for i in range(1, 5)})
        empty.update({f"t{i}_cost": 0.0 for i in range(1, 5)})
        if not rows:
            return empty

        first = rows[0]
        last = rows[-1]

        first_import = _safe_float(first.get("total_power_import_kwh"))
        last_import = _safe_float(last.get("total_power_import_kwh"))
        first_export = _safe_float(first.get("total_power_export_kwh"))
        last_export = _safe_float(last.get("total_power_export_kwh"))

        period_import = max(0.0, last_import - first_import)
        period_export = max(0.0, last_export - first_export)

        tariff_deltas: dict[int, float] = {}
        for tariff in (1, 2, 3, 4):
            key = f"total_power_import_t{tariff}_kwh"
            first_val = _safe_float(first.get(key))
            last_val = _safe_float(last.get(key))
            tariff_deltas[tariff] = max(0.0, last_val - first_val)

        if any(tariff_deltas.values()):
            costs = {t: tariff_deltas[t] * _get_tariff_rate(t, self.config) for t in tariff_deltas}
        else:
            # No per-tariff counter moved: bill the total at the active tariff.
            active_tariff = int(last.get("active_tariff", 1) or 1)
            if active_tariff not in tariff_deltas:
                active_tariff = 1
            tariff_deltas = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
            tariff_deltas[active_tariff] = period_import
            costs = {
                t: tariff_deltas[t] * _get_tariff_rate(t, self.config)
                for t in tariff_deltas
            }

        period_cost = (
            sum(costs.values()) - period_export * self.config.export_credit
        )

        result: dict[str, Any] = {
            "currency": self.config.currency,
            "period_import_kwh": round(period_import, 3),
            "period_export_kwh": round(period_export, 3),
            "period_cost": round(period_cost, 2),
            "total_cost": round(period_cost, 2),
            "total_export_kwh": round(period_export, 3),
            "export_credit": round(period_export * self.config.export_credit, 2),
        }
        for tariff in (1, 2, 3, 4):
            result[f"t{tariff}_import_kwh"] = round(tariff_deltas[tariff], 3)
            result[f"t{tariff}_rate"] = _get_tariff_rate(tariff, self.config)
            result[f"t{tariff}_cost"] = round(costs[tariff], 2)
        return result
