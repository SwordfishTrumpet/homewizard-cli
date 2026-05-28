"""OBIS code lookup table for DSMR telegrams."""

_OBIS_TABLE = {
    "1-0:1.8.1": "Total imported energy, tariff 1 (peak) — kWh",
    "1-0:1.8.2": "Total imported energy, tariff 2 (off-peak) — kWh",
    "1-0:2.8.1": "Total exported energy, tariff 1 (peak) — kWh",
    "1-0:2.8.2": "Total exported energy, tariff 2 (off-peak) — kWh",
    "1-0:1.7.0": "Actual active power (+ = import) — kW",
    "1-0:2.7.0": "Actual active power (- = export) — kW",
    "1-0:32.7.0": "Phase 1 voltage — V",
    "1-0:31.7.0": "Phase 1 current — A",
    "1-0:21.7.0": "Phase 1 instant power — kW",
    "1-0:22.7.0": "Phase 2 instant power — kW",
    "0-0:1.0.0": "Timestamp of telegram",
    "0-0:96.1.1": "Meter serial number (electricity)",
    "0-0:96.14.0": "Current tariff (1=peak, 2=off-peak)",
    "0-0:96.7.21": "Short power failure count",
    "0-0:96.7.9": "Long power failure count",
    "1-0:99.97.0": "Power failure event log",
    "1-0:32.32.0": "Voltage sag count",
    "1-0:32.36.0": "Voltage swell count",
    "0-1:24.1.0": "Gas meter device type",
    "0-1:96.1.0": "Gas meter serial number",
    "0-1:24.2.1": "Gas reading (timestamp + value) — m³",
    "1-3:0.2.8": "DSMR/SMR version",
    "0-0:96.13.0": "Text message from energy supplier",
}


def lookup_obis(code: str) -> str | None:
    """Look up an OBIS code description."""
    if not code:
        return None
    return _OBIS_TABLE.get(code)


def list_obis_codes() -> dict[str, str]:
    """Return the full OBIS lookup table."""
    return dict(_OBIS_TABLE)
