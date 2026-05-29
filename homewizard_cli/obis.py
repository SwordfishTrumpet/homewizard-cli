"""OBIS code lookup table for DSMR telegrams."""

_OBIS_TABLE = {
    # Electricity - Totals
    "1-0:1.8.0": "Total imported energy — kWh",
    "1-0:1.8.1": "Total imported energy, tariff 1 (peak) — kWh",
    "1-0:1.8.2": "Total imported energy, tariff 2 (off-peak) — kWh",
    "1-0:2.8.0": "Total exported energy — kWh",
    "1-0:2.8.1": "Total exported energy, tariff 1 (peak) — kWh",
    "1-0:2.8.2": "Total exported energy, tariff 2 (off-peak) — kWh",
    # Electricity - Instantaneous (total)
    "1-0:1.7.0": "Actual active power (+ = import) — kW",
    "1-0:2.7.0": "Actual active power (- = export) — kW",
    # Electricity - Instantaneous (per phase, import)
    "1-0:21.7.0": "Active power L1 (import) — kW",
    "1-0:41.7.0": "Active power L2 (import) — kW",
    "1-0:61.7.0": "Active power L3 (import) — kW",
    # Electricity - Instantaneous (per phase, export)
    "1-0:22.7.0": "Active power L1 (export) — kW",
    "1-0:42.7.0": "Active power L2 (export) — kW",
    "1-0:62.7.0": "Active power L3 (export) — kW",
    # Electricity - Voltage
    "1-0:32.7.0": "Voltage L1 — V",
    "1-0:52.7.0": "Voltage L2 — V",
    "1-0:72.7.0": "Voltage L3 — V",
    # Electricity - Current
    "1-0:31.7.0": "Current L1 — A",
    "1-0:51.7.0": "Current L2 — A",
    "1-0:71.7.0": "Current L3 — A",
    # Electricity - Power Quality (voltage sags/swells)
    "1-0:32.32.0": "Voltage sags L1 — count",
    "1-0:52.32.0": "Voltage sags L2 — count",
    "1-0:72.32.0": "Voltage sags L3 — count",
    "1-0:32.36.0": "Voltage swells L1 — count",
    "1-0:52.36.0": "Voltage swells L2 — count",
    "1-0:72.36.0": "Voltage swells L3 — count",
    # Electricity - Power Quality (failures)
    "0-0:96.7.21": "Short power failure count",
    "0-0:96.7.9": "Long power failure count",
    "1-0:99.97.0": "Power failure event log",
    # Electricity - Threshold / Limiter
    "1-0:31.4.0": "Fuse threshold L1 — A",
    "1-0:51.4.0": "Fuse threshold L2 — A",
    "1-0:71.4.0": "Fuse threshold L3 — A",
    "1-0:17.0.0": "Actual threshold power — W",
    "1-0:96.5.5": "Actual power limit",
    # Administrative
    "0-0:1.0.0": "Timestamp of telegram",
    "0-0:96.1.1": "Meter serial number (electricity)",
    "0-0:96.1.4": "Equipment identifier (extra)",
    "0-0:96.14.0": "Current tariff (1=peak, 2=off-peak)",
    "0-0:96.3.10": "Historical switching events (switch positions)",
    "0-0:96.13.0": "Text message from energy supplier",
    "0-0:96.13.1": "Text message code",
    "1-3:0.2.8": "DSMR/SMR version",
    # Slave meter - Gas (slave 1)
    "0-1:24.1.0": "Gas meter device type",
    "0-1:96.1.0": "Gas meter serial number",
    "0-1:24.2.1": "Gas reading (timestamp + value) — m³",
    # Slave meter - Water (slave 2)
    "0-2:24.1.0": "Water meter device type",
    "0-2:96.1.0": "Water meter serial number",
    "0-2:24.2.1": "Water reading (timestamp + value) — m³",
    # Slave meter - Heat (slave 3)
    "0-3:24.1.0": "Heat meter device type",
    "0-3:96.1.0": "Heat meter serial number",
    "0-3:24.2.1": "Heat reading (timestamp + value) — variable",
    # Slave meter - Cooling (slave 4)
    "0-4:24.1.0": "Cooling meter device type",
    "0-4:96.1.0": "Cooling meter serial number",
    "0-4:24.2.1": "Cooling reading (timestamp + value) — variable",
}


def lookup_obis(code: str) -> str | None:
    """Look up an OBIS code description."""
    if not code:
        return None
    return _OBIS_TABLE.get(code)


def list_obis_codes() -> dict[str, str]:
    """Return the full OBIS lookup table."""
    return dict(_OBIS_TABLE)
