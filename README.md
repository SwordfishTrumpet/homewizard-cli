# homewizard-cli

<p align="center">
  <img src="https://img.shields.io/github/license/SwordfishTrumpet/homewizard-cli?label=License" alt="MIT License">
  <img src="https://img.shields.io/badge/code%20style-ruff-blueviolet" alt="Ruff">
  <img src="https://img.shields.io/badge/types-pydantic%20v2-aa4488" alt="Pydantic v2">
  <img src="https://img.shields.io/badge/coverage-92%25-brightgreen" alt="Coverage 92%">
</p>

**A high-performance, feature-complete CLI for the HomeWizard P1 Meter.** Read real-time and cumulative energy data, monitor power quality, access raw DSMR telegrams, export to third-party systems (InfluxDB, MQTT, Prometheus, CSV/JSON), serve a REST proxy, view a live TUI dashboard, and manage device settings — all from the command line.

Supports both **API v1** (HTTP, port 80, no auth) and **API v2** (HTTPS, port 443, Bearer token auth) with automatic device discovery via mDNS.

---

## Table of Contents

- [Core Features](#core-features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [`homewizard-cli` (default)](#homewizard-cli-default)
  - [`data`](#data)
  - [`power`](#power)
  - [`energy`](#energy)
  - [`gas`](#gas)
  - [`quality`](#quality)
  - [`telegram`](#telegram)
  - [`info`](#info)
  - [`system`](#system)
  - [`identify`](#identify)
  - [`ping`](#ping)
  - [`discover`](#discover)
  - [`dashboard`](#dashboard)
  - [`export`](#export)
  - [`serve`](#serve)
  - [`reboot`](#reboot)
  - [`pair`](#pair)
  - [`users`](#users)
  - [`batteries`](#batteries)
  - [`state`](#state)
  - [`water`](#water)
  - [`combined`](#combined)
  - [`hass`](#hass)
  - [`cost`](#cost)
  - [`config`](#config)
- [Output Formats](#output-formats)
- [API Versioning](#api-versioning)
- [Global Options](#global-options)
- [Host Discovery](#host-discovery)
- [WebSocket Support](#websocket-support)
- [Expression Conditions (`--until`)](#expression-conditions---until)
- [JSONPath Queries (`--query`)](#jsonpath-queries---query)
- [Delta Tracking (`--delta`)](#delta-tracking---delta)
- [Template Output (`--template`)](#template-output---template)
- [Rate Limit Warning](#rate-limit-warning)
- [Configuration](#configuration)
- [Shell Completions](#shell-completions)
- [Error Handling](#error-handling)
- [SSL Certificate Handling (v2)](#ssl-certificate-handling-v2)
- [Proxy Support](#proxy-support)
- [systemd Service](#systemd-service)
- [Development](#development)
- [License](#license)

---

## Core Features

- **One-shot reads** — Instant power, energy, gas, voltage, and quality data in <100ms
- **Watch mode** — Poll at configurable intervals with Rich-formatted tables
- **WebSocket push** — Real-time data streaming via `wss://` (v2 only, optional `websockets` dep)
- **Delta tracking** — Show only changed values with colored green/red deltas
- **Tariff breakdown** — T1–T4 peak/off-peak import/export breakdowns
- **3-phase support** — L1/L2/L3 voltage, current, and power readings (optional fields)
- **Power quality events** — Sag/swell counters across up to 3 phases, power failure event logs
- **Raw DSMR telegrams** — Full OBIS telegram access with CRC validation, OBIS querying, and JSON parsing
- **Rich TUI dashboard** — Full-screen real-time dashboard with live sparklines
- **Data export** — Stream to InfluxDB, MQTT, Prometheus, CSV, JSON, TSV, env, or raw formats
- **File rotation** — Daily or hourly rotation for log files
- **Prometheus metrics** — Built-in HTTP metrics endpoint for Prometheus scraping
- **PID file** — Process management with stale PID detection
- **HTTP proxy server** — FastAPI + uvicorn REST proxy with optional response caching
- **v2 device management** — Reboot, pair tokens, list/delete users, control Plug-In Batteries
- **Configuration file** — Persistent host, timeout, format, and export defaults via `~/.config/homewizard-cli/config.toml`
- **Auto-discovery** — Zero-config mDNS discovery with 24-hour caching
- **Multi-format output** — Table (Rich), JSON, CSV, TSV, InfluxDB line protocol, Prometheus exposition, env, minimal, raw
- **JSONPath queries** — Extract specific fields with `--query "$.field_name"`
- **Go-style template** — Custom output with `--template "{{.field}}W"` syntax
- **Expression conditions** — `--until "active_power_w > 1000"` for automated exit
- **Graceful signal handling** — SIGINT/SIGTERM for clean shutdown of export streams
- **Energy cost calculator** — Real-time and historical cost breakdowns with configurable tariff rates (T1–T4, export credit)
- **SQLite historical data store** — Optional `--db` flag on any data-fetching command logs readings to a local SQLite database; `history` subcommand queries, aggregates, compares, and analyzes stored data

---

## Architecture & Tech Stack

| Component            | Library                   | Purpose                            |
|----------------------|---------------------------|------------------------------------|
| Component            | Library                   | Version | Purpose                            |
|----------------------|---------------------------|---------|------------------------------------|
| CLI framework        | [Typer](https://typer.tiangolo.com/) | 0.26+ | Command routing, shell completions |
| HTTP client          | [httpx](https://www.python-httpx.org/) | 0.28+ | Async HTTP/HTTPS requests          |
| Data models          | [Pydantic](https://docs.pydantic.dev/) | 2.13+ | Response validation, v1↔v2 mapping |
| Terminal output      | [Rich](https://rich.readthedocs.io/) | 15+ | Tables, panels, colors, sparklines |
| mDNS discovery       | [python-zeroconf](https://github.com/python-zeroconf/python-zeroconf) | 0.149+ | Network device discovery |
| Config parsing       | `tomllib` (stdlib)        | — | TOML config file parsing           |
| Optional: WebSocket  | [websockets](https://websockets.readthedocs.io/) | 16+ | Real-time data push (v2)  |
| Optional: REST proxy | [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) | 0.136+ / 0.48+ | HTTP proxy server for `/api/*` |
| Optional: MQTT       | [paho-mqtt](https://www.eclipse.org/paho/) | 2.1+ | MQTT broker publishing            |

**Design principles:** Single HTTP request per command, async/await throughout, connection reuse, lazy loading of optional deps, never-comment patterns, typed error hierarchy with exit codes.

---

## Installation

### Prerequisites

- **Python 3.11 or later**
- A HomeWizard P1 Meter on your local network
- Firmware 3.x–4.x for API v1, or firmware 6.x+ for full API v2 support

### Install from PyPI

```bash
pip install homewizard-cli
```

### Install with optional dependencies

```bash
pip install homewizard-cli[ws]     # WebSocket support (data --ws)
pip install homewizard-cli[dev]    # Development + all optional deps (testing, proxy server)
```

### Install from source

```bash
pip install git+https://github.com/SwordfishTrumpet/homewizard-cli
```

### Verify installation

```bash
homewizard-cli --version
```

---

## Quick Start

```bash
# Show a summary of current power usage (auto-discovers device)
homewizard-cli
```

```
P1 Meter at 192.168.1.100
WiFi: MyNetwork (78%)
456.8 W  Import:  12,345.68 kWh  Export:  2,345.68 kWh  Gas:  9,876.54 m³
```

```bash
# Discover your P1 meter on the network
homewizard-cli discover
```

```
Found device at 192.168.1.100
```

```bash
# Real-time power consumption
homewizard-cli power
```

```
456.8 W  (importing)
```

```bash
# Full data dump (Rich table)
homewizard-cli data
```

```
┌──────────────────────────────┬─────────────┐
│ Field                        │ Value       │
├──────────────────────────────┼─────────────┤
│ active_power_w               │ 456.789     │
│ total_power_import_kwh       │ 12345.678   │
│ ...                          │ ...         │
└──────────────────────────────┴─────────────┘
```

```bash
# Health check
homewizard-cli ping
```

```
P1 Meter at 192.168.1.100 — OK (42ms)
```

---

## Commands

### `homewizard-cli` (default)

When invoked without a subcommand, prints a flat table of the most important live data fields using Rich.

```
Field                          Value
─────────────────────────────────────────
wifi_ssid                      MyNetwork
wifi_strength                  78
smr_version                    50
meter_model                    SDM230
unique_id                      A1B2C3D4E5F6
active_tariff                  1
total_power_import_kwh         12345.678
total_power_import_t1_kwh      8234.567
total_power_import_t2_kwh      4111.111
total_power_export_kwh         2345.678
total_power_export_t1_kwh      1234.567
total_power_export_t2_kwh      1111.111
active_power_w                 456.789
total_gas_m3                   9876.543
```

### `data`

Full energy data with rich filtering, streaming, and output control.

```bash
# One-shot dump (all fields, Rich table)
homewizard-cli data

# Poll every 2 seconds
homewizard-cli data --watch 2

# Select specific fields
homewizard-cli data --fields active_power_w,active_voltage_l1_v,total_gas_m3

# Show only changed values (delta tracking)
homewizard-cli data --watch 2 --delta

# Custom Go-style template
homewizard-cli data --template "{{.active_power_w}}W | {{.total_power_import_kwh}}kWh"

# JSONPath query
homewizard-cli data --query "$.active_power_w"

# Exit when condition is met
homewizard-cli data --watch 1 --until "active_power_w > 1000"

# Real-time WebSocket push (v2 only)
homewizard-cli data --ws
homewizard-cli data --ws --watch 10
homewizard-cli data --ws --until "active_power_w > 5000"
```

**Options:**

| Option              | Description                                                 |
|---------------------|-------------------------------------------------------------|
| `--watch`           | Poll interval in seconds (default: 2s)                      |
| `--fields`          | Comma-separated field names to display (e.g. `active_power_w,total_gas_m3`) |
| `--template`        | Go-style output template (e.g. `{{.active_power_w}}W`)      |
| `--delta`           | Show only changed values with colored deltas (requires `--watch`) |
| `--query`           | JSONPath expression to filter data (e.g. `$.active_power_w`) |
| `--until`           | Exit when expression is true (e.g. `active_power_w > 1000`) |
| `--ws`              | Use WebSocket push instead of HTTP polling (v2 only)        |
| `--alert-webhook`   | Webhook URL to POST when `--until` condition fires          |
| `--alert-cmd`       | Shell command to run when `--until` condition fires         |
| `--alert-cooldown`  | Minimum seconds between alert dispatches (default: 0)       |
| `--agg`             | Show rolling aggregates (mean/min/max/stddev) when watching |
| `--format`          | Output format: `table`, `json`, `csv`, `tsv`, `influx`, `prometheus`, `env`, `minimal`, `raw` |

### `power`

Focused power readouts with optional sparkline trend.

```bash
# Simple one-shot
homewizard-cli power
```

```
456.8 W  (importing)
```

```bash
# Full details (import/export, voltage, current)
homewizard-cli power --full
```

```
Net:      456.8 W
Import:     456.8 W
Export:      0.0 W
Voltage:  238.5 V
Current:    1.9 A
```

```bash
# Color output (green=exporting, red=importing)
homewizard-cli power --color

# Sparkline trend (last 20 readings)
homewizard-cli power --sparkline
```

With `--full --sparkline`:

```
Net:      456.8 W
Import:     456.8 W
Export:      0.0 W
Voltage:  238.5 V
Current:    1.9 A
Trend:    ▃▃▄▄▅▆▇███▇▆▅▄▄▃▂▂▁▁
```

```bash
# Full + sparkline in watch mode
homewizard-cli power --full --sparkline --watch 1

# Watch until a condition
homewizard-cli power --watch --until "abs(active_power_w) > 2000"

# Machine-readable output
homewizard-cli power --format csv
```

**Options:**

| Option              | Description                                                 |
|---------------------|-------------------------------------------------------------|
| `--watch`           | Poll interval in seconds (default: 2s)                      |
| `--full`            | Show import/export breakdown, voltage, and current          |
| `--color`           | Color output: green when exporting, red when importing      |
| `--sparkline`       | Unicode sparkline of last 20 power readings (▁▂▃▄▅▆▇█)      |
| `--agg`             | Show rolling aggregates (mean/min/max/stddev) when watching |
| `--until`           | Exit when expression is true (e.g. `abs(active_power_w) > 2000`) |
| `--alert-webhook`   | Webhook URL to POST when `--until` condition fires          |
| `--alert-cmd`       | Shell command to run when `--until` condition fires         |
| `--alert-cooldown`  | Minimum seconds between alert dispatches (default: 0)       |
| `--format`          | Output format: `table`, `json`, `csv`, `tsv`                |

### `energy`

Cumulative energy readings (kWh) with tariff breakdowns.

```bash
# Import/export/net totals
homewizard-cli energy
```

```
Import:  12,345.68 kWh
Export:   2,345.68 kWh
Net:     10,000.00 kWh consumed
```

```bash
# With tariff breakdown (T1–T4 when available)
homewizard-cli energy --tariffs
```

```
Import:  12,345.68 kWh
Export:   2,345.68 kWh
Net:     10,000.00 kWh consumed

T1 (peak):     Import: 8,234.57  Export: 1,234.57
T2 (off-peak): Import: 4,111.11  Export: 1,111.11
```

**Options:**

| Option      | Description                                              |
|-------------|----------------------------------------------------------|
| `--tariffs` | Show T1–T4 tariff breakdown (T3/T4 only if supported)   |

### `gas`

Gas consumption in m³, with optional watch mode.

```bash
# Simple reading
homewizard-cli gas
```

```
9,876.54 m³
```

```bash
# Full details (total, last read timestamp, meter ID)
homewizard-cli gas --full
```

```
Total:     9,876.54 m³
Last read: 2026-05-29 12:00:00
Meter ID:  G1H2I3J4K5L6
```

```bash
# Watch mode
homewizard-cli gas --watch 10
```

**Options:**

| Option    | Description                                              |
|-----------|----------------------------------------------------------|
| `--full`  | Show total m³, last read timestamp, and meter ID        |
| `--watch` | Poll interval in seconds (default: 2s)                   |

### `quality`

Power quality monitoring — voltage sags, swells, and power failure counters across up to 3 phases.

```bash
# All counters (L1–L3 sag/swell when available)
homewizard-cli quality
```

```
Voltage Sags L1: 2
Voltage Swells L1: 0
Voltage Sags L2: 1
Voltage Swells L2: 0
Voltage Sags L3: 0
Voltage Swells L3: 0
Short Failures:  0
Long Failures:   0
```

```bash
# Alert mode — only print when counts change
homewizard-cli quality --watch --alert

# Show power failure event log (parsed from DSMR telegram)
homewizard-cli quality --events
```

```
Voltage Sags L1: 3
Voltage Swells L1: 0
Short Failures:  1
Long Failures:   0

Power Failure Events:
  2026-05-28 14:23:00 — Short outage (2 s)
```

**Options:**

| Option     | Description                                                    |
|------------|----------------------------------------------------------------|
| `--watch`  | Poll interval in seconds (default: 2s)                         |
| `--alert`  | Only print when any sag/swell counter changes (requires `--watch`) |
| `--events` | Show power failure event log (timestamps and durations)        |

### `telegram`

Access the raw DSMR telegram for low-level diagnostics.

```bash
# Raw output
homewizard-cli telegram
```

```
/XMX5LGBBFG123456789

0-0:1.0.0.0(260529120000W)
1-0:1.8.1(00012345.678*kWh)
1-0:1.8.2(00004111.111*kWh)
1-0:2.8.1(00001234.567*kWh)
1-0:2.8.2(00001111.111*kWh)
1-0:1.7.0(000456.789*kW)
1-0:21.7.0(000456.789*kW)
1-0:32.7.0(000238.5*V)
1-0:31.7.0(000001.9*A)
0-0:96.7.19(00002)
0-0:96.7.9(00000)
0-1:24.2.1(260529120000W)(09876.543*m3)
!522F
```

```bash
# Validate CRC
homewizard-cli telegram --validate
```

```
CRC: 522F — Valid
```

```bash
# Parse into JSON
homewizard-cli telegram --format json
```

```json
{
  "header": "/XMX5LGBBFG123456789",
  "timestamp": "260529120000W",
  "obis": {
    "0-0:1.0.0.0": "260529120000W",
    "1-0:1.8.1": "00012345.678*kWh",
    "1-0:1.8.2": "00004111.111*kWh",
    "1-0:2.8.1": "00001234.567*kWh",
    "1-0:2.8.2": "00001111.111*kWh",
    "1-0:1.7.0": "000456.789*kW",
    "1-0:21.7.0": "000456.789*kW",
    "1-0:32.7.0": "000238.5*V",
    "1-0:31.7.0": "000001.9*A",
    "0-0:96.7.19": "00002",
    "0-0:96.7.9": "00000",
    "0-1:24.2.1": "260529120000W(09876.543*m3"
  },
  "crc": "522F",
  "valid": true
}
```

```bash
# Parse with human-readable OBIS names
homewizard-cli telegram --format json --named
```

```json
{
  "header": "/XMX5LGBBFG123456789",
  "timestamp": "260529120000W",
  "obis": {
    "Timestamp of telegram": "260529120000W",
    "Total imported energy, tariff 1 (peak) — kWh": "00012345.678*kWh",
    "Total imported energy, tariff 2 (off-peak) — kWh": "00004111.111*kWh",
    "Total exported energy, tariff 1 (peak) — kWh": "00001234.567*kWh",
    "Total exported energy, tariff 2 (off-peak) — kWh": "00001111.111*kWh",
    "Actual active power (+ = import) — kW": "000456.789*kW",
    "Active power L1 (import) — kW": "000456.789*kW",
    "Voltage L1 — V": "000238.5*V",
    "Current L1 — A": "000001.9*A",
    "Short power failure count": "00002",
    "Long power failure count": "00000",
    "Gas reading (timestamp + value) — m³": "260529120000W(09876.543*m3"
  },
  "crc": "522F",
  "valid": true
}
```

```bash
# Extract a specific OBIS code
homewizard-cli telegram --obis 1-0:1.8.1

# Explain what an OBIS code means
homewizard-cli telegram --explain 1-0:1.8.1
```

```
1-0:1.8.1 — Total import energy (T1, peak)
```

```bash
# Count telegrams per minute
homewizard-cli telegram --watch --rate
```

**Options:**

| Option       | Description                                                   |
|--------------|---------------------------------------------------------------|
| `--validate` | Validate the CRC checksum of the telegram                      |
| `--obis`     | Extract a specific OBIS code value (e.g. `1-0:1.8.1`)         |
| `--explain`  | Show human-readable description of an OBIS code               |
| `--named`    | Replace OBIS codes with human-readable names in JSON output   |
| `--watch`    | Poll interval in seconds (default: 2s)                         |
| `--rate`     | Count and display telegrams per minute (requires `--watch`)   |
| `--format`   | Output format: `json`, `table`, `csv`, `tsv`, `raw`           |

### `info`

Device information and metadata.

```bash
homewizard-cli info
```

**v2 output:**

```
Product:     P1 Meter
Type:        HWE-P1
Serial:      A1B2C3D4E
Firmware:    4.2.1
API:         v2
WiFi:        MyNetwork (-42 dBm)
Cloud:       enabled
```

**v1 output:**

```
Product:     P1 Meter
Type:        HWE-P1
Serial:      A1B2C3D4E
Firmware:    3.8.0
API:         v1
WiFi:        MyNetwork (78%)
Meter:       SDM230
DSMR:        5.0
Cloud:       enabled
```

**Options:** *(none — uses global options for host, timeout, etc.)*

### `system`

Read and modify device system settings.

```bash
# Read all v2 system settings
homewizard-cli system
```

```
┌───────────────────────────┬───────────┐
│ Field                     │ Value     │
├───────────────────────────┼───────────┤
│ cloud_enabled             │ True      │
│ wifi_ssid                 │ MyNetwork │
│ wifi_rssi_db              │ -42.0     │
│ uptime_s                  │ 86400     │
│ status_led_brightness_pct │ 100       │
│ api_v1_enabled            │ True      │
└───────────────────────────┴───────────┘
```

```bash
# Toggle cloud connection
homewizard-cli system --cloud-toggle

# Set cloud explicitly
homewizard-cli system --cloud false
homewizard-cli system --cloud true

# Set LED brightness (v2 only, 0–100)
homewizard-cli system --led-brightness 50

# v1 fallback (only cloud_enabled is writable)
homewizard-cli system --api-version v1
homewizard-cli system --api-version v1 --cloud false
```

**Options:**

| Option            | Description                                                           |
|-------------------|-----------------------------------------------------------------------|
| `--cloud`         | Set `cloud_enabled` to `true` or `false` (e.g. `--cloud false`)       |
| `--cloud-toggle`  | Toggle the current `cloud_enabled` value                               |
| `--led-brightness`| Set LED brightness (0–100, v2 only)                                   |

### `identify`

Physically identify the device by blinking its LED.

```bash
homewizard-cli identify
```

```
LED blink triggered on P1 Meter (1x)
```

```bash
homewizard-cli identify --count 5
```

```
LED blink triggered on P1 Meter (5x)
```

**Options:**

| Option    | Description                          |
|-----------|--------------------------------------|
| `--count` | Number of LED blinks (default: 1)    |

### `ping`

Quick connectivity check with response time.

```bash
homewizard-cli ping
```

```
P1 Meter at 192.168.1.100 — OK (42ms)
```

```bash
# Exit code only (0 = success, non-zero = failure)
homewizard-cli ping --quiet
```

**Options:**

| Option    | Description                                           |
|-----------|-------------------------------------------------------|
| `--quiet` | Exit code only — no output (0=success, non-zero=fail) |

### `discover`

Discover HomeWizard devices on the local network via mDNS.

```bash
# Find the first device
homewizard-cli discover
```

```
Found device at 192.168.1.100
```

```bash
# Verbose output with cache info
homewizard-cli discover --verbose
```

```
Discovering P1 meter (timeout=3.0s) ...
Found device at 192.168.1.100
```

```bash
# Save discovered host to cache (~/.config/homewizard-cli/host, 24h TTL)
homewizard-cli discover --save

# List ALL HomeWizard devices on the network
homewizard-cli discover --all
```

```
┌───────────────┬──────────┬──────────┬──────────┐
│ IP            │ Product  │ Serial   │ Name     │
├───────────────┼──────────┼──────────┼──────────┤
│ 192.168.1.100 │ P1 Meter │ A1B2C3D4 │ P1 Meter │
│ 192.168.1.101 │ HWE-SG   │ E5F6G7H8 │ SmartPlug│
└───────────────┴──────────┴──────────┴──────────┘
```

Discovery attempts `_homewizard._tcp.local.` (v2 devices) first, then falls back to `_hwenergy._tcp.local.` (v1 legacy), and finally scans `/proc/net/arp` for known TP-Link MAC prefixes (`5c:62:8b`, `3c:61:05`).

**Options:**

| Option      | Description                                                   |
|-------------|---------------------------------------------------------------|
| `--save`    | Persist discovered host to cache (~/.config/homewizard-cli/host) |
| `--all`     | List every HomeWizard device on the network                   |
| `--verbose` | Show mDNS query progress and cache status                     |

### `dashboard`

Full-screen real-time dashboard with Rich Live/Layout display.

```bash
homewizard-cli dashboard
homewizard-cli dashboard --watch 5
```

```
┌────────────────────────────────────────────────────────┐
│ P1 Meter — SDM230  |  WiFi: MyNetwork (78%)            │
└────────────────────────────────────────────────────────┘
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Power        │ │ Energy       │ │    Gas       │
│              │ │              │ │              │
│ 456 W        │ │ Import       │ │ 9,876.54 m³  │
│ (importing)  │ │   12,345.68  │ │              │
│              │ │ Export       │ │              │
│ Voltage      │ │    2,345.68  │ │              │
│   238.5 V    │ │ Net          │ │              │
│              │ │   10,000.00  │ │              │
│ Current      │ │              │ │              │
│   1.9 A      │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
┌────────────────────────────────────────────────────────┐
│ Power Sparkline (last 40 samples)                      │
│ ▃▃▄▄▅▆▇███▇▆▅▄▄▃▂▂▁▁▂▃▄▅▆▇██▇▆▅▄▃▂▁▁▂▃▄▅▆▇             │
└────────────────────────────────────────────────────────┘
```

**Options:**

| Option    | Description                               |
|-----------|-------------------------------------------|
| `--watch` | Update interval in seconds (default: 2s)  |

### `export`

Continuous export to file, MQTT, or stdout with rotation, metrics, and PID file support.

```bash
# Export to InfluxDB line protocol (default format)
homewizard-cli export --watch 10

# Export to CSV file
homewizard-cli export --format csv --file readings.csv --watch 60

# Export with daily file rotation
homewizard-cli export --format json --file p1.log --watch 60 --rotate daily

# Hourly rotation
homewizard-cli export --format json --file readings.log --watch 30 --rotate hourly

# Publish to MQTT
homewizard-cli export --format mqtt --broker mqtt://broker.local --topic home/p1meter --watch 30
homewizard-cli export --format mqtt --broker mqtt://broker.local --topic home/p1meter --qos 2

# Skip writes when data hasn't changed
homewizard-cli export --format json --file readings.log --watch 10 --skip-unchanged

# Only show changed fields (delta mode)
homewizard-cli export --watch 5 --delta

# Stop when condition is met
homewizard-cli export --watch 2 --until "total_power_import_kwh > 10000"

# Enable Prometheus metrics endpoint on port 9090
homewizard-cli export --watch 10 --metrics-port 9090

# Write PID file for process management
homewizard-cli export --watch 10 --pid-file /var/run/hw-export.pid

# Pipe to external systems
homewizard-cli export --format json --watch 2 | curl -X POST http://influxdb:8086/write?db=energy --data-binary @-
```

**Options:**

| Option            | Description                                                         |
|-------------------|---------------------------------------------------------------------|
| `--watch`         | Poll interval in seconds (required for continuous export)            |
| `--format`        | Output format: `influx`, `json`, `csv`, `tsv`, `mqtt`, `prometheus`, `env`, `minimal`, `raw` |
| `--file`          | Write output to a file instead of stdout                            |
| `--rotate`        | Rotate log files: `daily` (YYYY-MM-DD) or `hourly` (YYYY-MM-DDTHH)  |
| `--broker`        | MQTT broker URL (required for `--format mqtt`)                      |
| `--topic`         | MQTT publish topic (required for `--format mqtt`)                   |
| `--qos`           | MQTT QoS level (0, 1, or 2)                                         |
| `--skip-unchanged`| Skip writing when data hasn't changed since last poll                |
| `--fields`        | Comma-separated field names to export (e.g. `active_power_w`)       |
| `--delta`         | Show only changed fields with colored deltas (requires `--watch`)   |
| `--agg`           | Show rolling aggregates (mean/min/max/stddev) when watching         |
| `--until`         | Exit when expression is true (e.g. `total_power_import_kwh > 10000`)|
| `--alert-webhook`  | Webhook URL to POST when `--until` condition fires          |
| `--alert-cmd`      | Shell command to run when `--until` condition fires         |
| `--alert-cooldown` | Minimum seconds between alert dispatches (default: 0)       |
| `--metrics-port`  | Enable Prometheus metrics HTTP endpoint on this port (0=disabled)   |
| `--pid-file`      | Write PID to file for process management (removed on exit)          |
| `--db`            | SQLite database path for historical logging (e.g. `energy.db`)      |
| `--retain-days`   | Auto-prune rows older than N days (never by default)                |

#### Export Features

- **Exponential backoff** — On fetch/write errors, retry with backoff starting at 1s, doubling up to 60s max. Resets after a successful fetch.
- **Signal handling** — Listens for SIGINT and SIGTERM for graceful shutdown: closes MQTT connections, flushes file handles, stops the metrics server, removes the PID file.
- **Metrics server** (`--metrics-port`) — Exposes Prometheus-format metrics at `GET /metrics`:
  - `homewizard_readings_total` — Successful readings counter
  - `homewizard_errors_total` — Error counter
  - `homewizard_last_poll_timestamp_seconds` — Unix timestamp of last successful poll
  - `--metrics-port 0` disables the metrics endpoint (default)
- **PID file** (`--pid-file`) — Writes PID on startup, removes on exit. Detects stale PIDs (process no longer alive) and refuses to start if an existing process is already running (exit code 1).
- **File rotation** (`--rotate`) — Supports `daily` (appends `YYYY-MM-DD` to filename) and `hourly` (appends `YYYY-MM-DDTHH`). Previous file is renamed before a new one is opened.

### `serve`

Start a FastAPI + uvicorn proxy server that forwards requests to the P1 meter. Requires `fastapi` and `uvicorn` (install via `pip install homewizard-cli[dev]`).

```bash
homewizard-cli serve
```

```
P1 Meter at 192.168.1.100 — OK
Starting proxy at http://0.0.0.0:8000
Proxying to P1 Meter at 192.168.1.100
```

```bash
homewizard-cli serve --port 9000 --cache 10
```

Then query the proxy:

```bash
curl http://localhost:8000/api/measurement  # v2
curl http://localhost:8000/api/v1/data      # v1
```

**Features:**
- Proxies all `/api/*` paths to the P1 meter
- Optional response caching (in-memory, TTL in seconds)
- Supports both API v1 (HTTP) and v2 (HTTPS + Bearer auth)
- Validates device connectivity before starting

**Options:**

| Option    | Description                                           |
|-----------|-------------------------------------------------------|
| `--bind`  | Bind address (default: `0.0.0.0`)                     |
| `--port`  | Listen port (default: `8000`)                         |
| `--cache` | Cache proxied responses for N seconds (default: 0, disabled) |

### `reboot`

Reboot the device (v2 only, requires `--token`).

```bash
homewizard-cli reboot --token <token>
```

```
Reboot result: {"status": "ok"}
```

### `pair`

Create an API v2 auth token. Press the physical button on the device within 30 seconds, then run:

```bash
homewizard-cli pair
```

```
User:  local/cli
Token: abc123def456...
```

```bash
homewizard-cli pair --name local/myapp
```

### `users`

Manage API v2 users (v2 only, requires `--token`).

```bash
# List users
homewizard-cli users list --token <token>
```

```
┌─────────────┐
│ Name        │
├─────────────┤
│ local/cli   │
│ local/admin │
└─────────────┘
```

```bash
# Delete a user (revokes token)
homewizard-cli users delete --name local/admin --token <token>
```

```
Deleted: {"status": "ok"}
```

### `batteries`

Manage HomeWizard Plug-In Battery state (v2 only, requires `--token`).

```bash
# Get battery state
homewizard-cli batteries --token <token>
```

```json
{
  "mode": "to_full",
  "permissions": ["charge_to_full", "target_power"],
  "charge_to_full": true,
  "battery_count": 2,
  "power_w": -1500.0,
  "target_power_w": -2000.0,
  "max_consumption_w": 1500.0,
  "max_production_w": 2000.0
}
```

```bash
# Set battery mode
homewizard-cli batteries --mode to_full --token <token>
```

```
Set mode to to_full: {"status": "ok"}
```

Valid modes: `to_full`, `zero`, `standby`, `predictive`

### `state`

Get or set Energy Socket state (power, switch lock, brightness).

```bash
# Read current state
homewizard-cli state

# Turn socket on
homewizard-cli state --power-on

# Turn socket off
homewizard-cli state --power-off

# Set LED brightness
homewizard-cli state --brightness 50

# Lock switch
homewizard-cli state --switch-lock
```

**Options:**

| Option            | Description                                              |
|-------------------|----------------------------------------------------------|
| `--power-on`      | Turn the socket on                                       |
| `--power-off`     | Turn the socket off                                      |
| `--switch-lock`   | Lock the switch (prevent manual toggling)                |
| `--switch-unlock` | Unlock the switch                                        |
| `--brightness`    | LED brightness (0–100)                                   |

---

### `water`

Display water meter readings (flow and total consumption).

```bash
# Simple reading
homewizard-cli water

# Full details
homewizard-cli water --full

# Watch mode
homewizard-cli water --watch 10
```

**Options:**

| Option    | Description                                              |
|-----------|----------------------------------------------------------|
| `--full`  | Show total m³, flow L/min, last read timestamp, meter ID |
| `--watch` | Poll interval in seconds (default: 2s)                     |

---

### `combined`

Fetch all device models (device info, measurement, system, state, batteries) in parallel.

```bash
# One-shot combined data
homewizard-cli combined

# With explicit host
homewizard-cli combined --host 192.168.1.100
```

---

### `hass`

Generate Home Assistant discovery configuration (MQTT or REST).

```bash
# MQTT discovery topics (default)
homewizard-cli hass --mqtt
```

```json
{"topic": "homeassistant/sensor/ABC123/power/config", "payload": {"name": "P1 Meter Power", "state_topic": "homewizard/ABC123/state", "unit_of_measurement": "W", "device_class": "power", "state_class": "measurement", "unique_id": "ABC123_power", "device": {"identifiers": ["ABC123"], "name": "P1 Meter", "model": "HWE-P1", "manufacturer": "HomeWizard"}}}
```

```bash
# REST configuration.yaml entries
homewizard-cli hass --rest
```

```json
{"sensor": [{"platform": "rest", "name": "Power", "device_class": "power", "value_template": "{{ value_json.active_power_w }}", "device": {"identifiers": ["ABC123"], "name": "P1 Meter", "manufacturer": "HomeWizard"}}]}
```

Generates 7 sensors: Power, Energy Import, Energy Export, Gas, Water, Voltage L1, Current L1. Defaults to MQTT mode if neither `--mqtt` nor `--rest` is specified.

**Options:**

| Option           | Description                                                       |
|------------------|-------------------------------------------------------------------|
| `--mqtt`         | Output MQTT discovery topic/payload pairs (one per sensor)        |
| `--rest`         | Output a single `configuration.yaml` structure with all sensors   |
| `--topic-prefix` | MQTT state topic prefix (default: `homewizard`)                   |

---

### `cost`

Calculate energy costs from real-time or historical data using configurable tariff rates.

```bash
# Real-time cost from current meter reading
homewizard-cli cost

# Tariff breakdown table
homewizard-cli cost --tariffs

# Today's cost from historical DB
homewizard-cli cost --today --db energy.db

# Yesterday's cost
homewizard-cli cost --yesterday --db energy.db

# This month's cost
homewizard-cli cost --this-month --db energy.db

# Live cost ticker updating every 5 seconds
homewizard-cli cost --watch 5

# Custom rates
homewizard-cli cost --t1-rate 0.35 --t2-rate 0.25 --currency USD
```

**Output example:**

```
Current Cost Breakdown:
┌─────────────┬──────────┬───────┬─────────┐
│ Tariff      │ kWh      │ Rate  │ Cost    │
├─────────────┼──────────┼───────┼─────────┤
│ T1 (peak)   │ 8,234.57 │ 0.30€ │ 2,470.37€ │
│ T2 (off-peak│ 4,111.11 │ 0.20€ │ 822.22€  │
│ Export      │ 2,345.68 │ 0.10€ │ -234.57€ │
├─────────────┼──────────┼───────┼─────────┤
│ Total       │          │       │ 3,058.02€ │
└─────────────┴──────────┴───────┴─────────┘
```

**Options:**

| Option              | Description                                                  |
|---------------------|--------------------------------------------------------------|
| `--tariffs`         | Show tariff breakdown table                                   |
| `--watch`           | Poll interval in seconds (default: 2s)                        |
| `--today`           | Calculate today's cost from historical DB                       |
| `--yesterday`       | Calculate yesterday's cost from historical DB                   |
| `--this-month`      | Calculate this month's cost from historical DB                  |
| `--db`              | SQLite database path (default: `~/.config/homewizard-cli/energy.db`) |
| `--t1-rate`         | T1 tariff rate (€/kWh)                                         |
| `--t2-rate`         | T2 tariff rate (€/kWh)                                         |
| `--t3-rate`         | T3 tariff rate (€/kWh)                                         |
| `--t4-rate`         | T4 tariff rate (€/kWh)                                         |
| `--export-credit`   | Export credit per kWh (€/kWh)                                  |
| `--currency`        | Currency symbol (default: EUR)                               |

**Config file:** Add `[tariffs]` to `~/.config/homewizard-cli/config.toml`:
```toml
[tariffs]
t1_rate = 0.30
t2_rate = 0.20
export_credit = 0.10
currency = "EUR"
```

---

### `config`

Configuration management.

```bash
# Validate config file
homewizard-cli config --validate

# Show config file location and contents
homewizard-cli config --show
```

---

### `history`

Query historical data previously logged to a SQLite database via `--db` on data-fetching commands. Pure local queries — no HTTP calls to the device.

```bash
# DB metadata
homewizard-cli history --info
```

```
Database:    ~/.config/homewizard-cli/energy.db
Size:        4.2 MB
Rows:        87,402
Devices:     1 (ABC123 — P1 Meter)
Date range:  2026-03-14 08:00:00 .. 2026-05-29 14:32:00
Completeness: 94.3%
```

```bash
# Yesterday's hourly power profile
homewizard-cli history --yesterday --agg hourly --field active_power_w

# This month's daily import/export as CSV
homewizard-cli history --this-month --agg daily --fields total_power_import_kwh,total_power_export_kwh --format csv

# Compare this week to last week
homewizard-cli history --this-week --compare last-week --fields active_power_w,total_power_import_kwh

# Peak power readings this month
homewizard-cli history --this-month --top 5 --field active_power_w

# Lowest gas readings
homewizard-cli history --this-month --bottom 5 --field total_gas_m3

# See what was logged while the exporter was down
homewizard-cli history --since-last --agg daily --field total_power_import_kwh

# List all devices in the DB
homewizard-cli history --list-devices

# Filter by device in a multi-device DB
homewizard-cli history --device-id ABC123 --yesterday --agg hourly --field active_power_w

# Reclaim disk space
homewizard-cli history --vacuum

# Custom DB path
homewizard-cli history --db /mnt/nas/archive.db --this-month --agg daily
```

**Options:**

| Option              | Description                                                      |
|---------------------|------------------------------------------------------------------|
| `--today`           | All rows from today                                              |
| `--yesterday`       | All rows from yesterday                                          |
| `--this-week`       | Monday 00:00 to now                                              |
| `--this-month`      | 1st 00:00 to now                                                 |
| `--range`           | Arbitrary date range, e.g. `"2026-05-01..2026-05-29"`           |
| `--since-last`      | Rows from the most recent stored timestamp to now                |
| `--compare`         | Delta vs prior period: `last-week`, `last-month`, `last-year`    |
| `--top`             | Top N readings for the selected field(s)                         |
| `--bottom`          | Bottom N readings for the selected field(s)                      |
| `--fields`          | Comma-separated field names (same as `data --fields`)            |
| `--device-id`       | Filter by device serial                                          |
| `--list-devices`    | Print all device serials in the DB                               |
| `--agg`             | Aggregate: `hourly`, `daily`, `weekly`, `monthly`                |
| `--info`            | DB metadata: row count, date range, devices, completeness, size  |
| `--vacuum`          | Reclaim disk space                                               |
| `--format`          | Output format (same as other commands)                           |
| `--db`              | SQLite database path (default: `~/.config/homewizard-cli/energy.db`, overridable via `HW_DB` env var) |

The default database path is `~/.config/homewizard-cli/energy.db`, which can be overridden with the `HW_DB` environment variable.

---

## Output Formats

Available on most data-output commands via `--format`:

| Format        | Description                                                |
|---------------|------------------------------------------------------------|
| `table`       | Rich formatted table (default in TTY)                      |
| `json`        | JSON object (default when piped/non-TTY)                   |
| `csv`         | Comma-separated values                                     |
| `tsv`         | Tab-separated values                                       |
| `influx`      | InfluxDB line protocol                                     |
| `prometheus`  | Prometheus exposition format                               |
| `env`         | `KEY=VALUE` lines                                          |
| `minimal`     | Tab-separated values, no header                            |
| `raw`         | Raw `field:value` pairs                                    |
| `mqtt`        | MQTT publish (`export` command only, requires `--broker`)  |

Format auto-detection: `table` in interactive terminals, `json` when piped.

---

## API Versioning

API v2 (HTTPS, port 443, Bearer token auth) is the default. Use `--api-version v1` to fall back to API v1 (HTTP, port 80, no auth).

```bash
homewizard-cli data                    # v2 (default)
homewizard-cli data --api-version v1   # v1 fallback

homewizard-cli info --token MY_TOKEN
homewizard-cli info --token MY_TOKEN --no-verify
```

### v1 ↔ v2 Mapping

| Feature      | v1                                   | v2                                    |
|--------------|--------------------------------------|---------------------------------------|
| Protocol     | HTTP (port 80)                       | HTTPS (port 443)                      |
| Auth         | None                                 | Optional Bearer token                 |
| Client       | `P1Client`                           | `P1ClientV2`                          |
| Data         | `/api/v1/data` → `DataResponse`      | `/api/measurement` → `MeasurementV2`  |
| System       | `/api/v1/system` → `SystemResponse`  | `/api/system` → `SystemV2`            |
| Device info  | `/api/` (dict)                       | `/api` → `DeviceInfoV2`               |
| Identify     | `PUT /api/v1/identify`               | `PUT /api/system/identify`            |
| Telegram     | `GET /api/v1/telegram` (raw)         | `GET /api/telegram` → `TelegramV2`    |
| mDNS Service | `_hwenergy._tcp.local.`              | `_homewizard._tcp.local.`             |

**v2-only commands** (no v1 equivalent): `reboot`, `pair`, `users list`, `users delete`, `batteries`

v2 measurement data is automatically mapped to v1 field names via the unified `Measurement` model so all formatters and display commands work seamlessly with both API versions. Fields without v2 equivalents (`wifi_ssid`, `wifi_strength`, `text_message`) default to empty values.

---

---

## Global Options

| Option            | Short | Default      | Description                                        |
|-------------------|-------|--------------|----------------------------------------------------|
| `--host`          | `-H`  | auto-discover| P1 meter IP address or hostname                   |
| `--timeout`       | `-t`  | `3.0`        | HTTP request timeout in seconds                    |
| `--proxy`         |       |              | HTTP proxy URL (scheme://host:port)                |
| `--format`        | `-f`  | `auto`       | Output format (see [Output Formats](#output-formats)) |
| `--no-color`      |       | `false`      | Disable ANSI colors                                |
| `--quiet`         | `-q`  | `false`      | Suppress non-error output                          |
| `--verbose`       | `-v`  | `false`      | Show HTTP request details                          |
| `--api-version`   |       | `v2`         | API version: `v1` or `v2`                          |
| `--token`         |       |              | API v2 Bearer token                                |
| `--no-verify`     |       | `false`      | Disable SSL certificate verification (v2)          |
| `--version`       |       |              | Show version and exit                              |

**Host resolution priority:** CLI `--host` > config file `[default].host` > hardcoded fallback `192.168.68.109`

---

## Host Discovery

`homewizard-cli discover` automatically finds your device without hardcoding an IP:

1. Queries `_homewizard._tcp.local.` (v2 mDNS service)
2. Falls back to `_hwenergy._tcp.local.` (v1 legacy mDNS service)
3. Falls back to ARP table scan — checks `/proc/net/arp` for TP-Link MAC prefixes `5c:62:8b` and `3c:61:05`
4. Caches the result to `~/.config/homewizard-cli/host` with a 24-hour TTL

The `--save` flag persists the discovered host to the cache. The `--all` flag returns every detected HomeWizard device on the network in a Rich table.

---

## Watch Mode (`--watch`)

Many commands support `--watch` (or `--watch N`), which turns a one-shot read into a continuous polling loop. Instead of fetching data once and exiting, the command polls the P1 meter every N seconds and prints the result each time.

```bash
homewizard-cli data --watch       # poll at default interval (2s)
homewizard-cli data --watch 5     # poll every 5 seconds
homewizard-cli power --watch 1    # poll every 1 second
homewizard-cli gas --watch 10     # poll every 10 seconds
```

Press Ctrl+C to stop. Polling intervals below 1.0s print a yellow warning since the device may become unresponsive.

Watch mode combines with other flags for powerful use cases:

| Combo                         | Effect                                                          |
|-------------------------------|-----------------------------------------------------------------|
| `--watch --delta`             | Only show fields whose values changed since last poll           |
| `--watch --sparkline`         | Sliding 20-sample sparkline trend chart (▁▂▃▄▅▆▇█)              |
| `--watch --until`             | Automatically exit when a condition is met                      |
| `--until --alert-webhook`    | Fire webhook on condition, keep watching in `--watch` mode      |
| `--until --alert-cmd`        | Run shell command on condition, keep watching in `--watch` mode |
| `--watch --alert`            | (quality) Only print when sag/swell counters change             |
| `--watch --rate`              | (telegram) Count and display telegrams per minute               |
| `--watch --skip-unchanged`    | (export) Skip writing to file/MQTT when data is unchanged       |

Commands supporting `--watch`: `data`, `power`, `gas`, `quality`, `telegram`, `dashboard`, `export`.

---

## WebSocket Support

The `data --ws` flag uses WebSocket push (v2 only, `wss://`) instead of HTTP polling. Data arrives in real time as the device emits it.

```bash
pip install homewizard-cli[ws]         # install websockets dependency
homewizard-cli data --ws               # one-shot: single message, then exit
homewizard-cli data --ws --watch 10    # idle timeout: close after 10s of inactivity
homewizard-cli data --ws --until "active_power_w > 5000"
```

Without `--watch`, a single message is received and the connection closes. With `--watch`, the value becomes the WebSocket idle timeout (defaults to 30s if not specified). The `websockets` package is loaded lazily — if missing, a clear error message is shown directing users to install `homewizard-cli[ws]`.

---

## Expression Conditions (`--until`)

Exit watch/data loops when a numeric field crosses a threshold:

```bash
--until "active_power_w > 1000"
--until "total_power_import_kwh >= 5000"
--until "abs(active_power_w) < 10"
--until "voltage_sag_l1_count != 0"
--until "active_voltage_l1_v <= 220"
```

Supports operators `>`, `<`, `>=`, `<=`, `==`, `!=`, and wrapping with `abs()`. Exits with code 10 when the condition is met.

---

## Alert Actions (`--alert-webhook`, `--alert-cmd`, `--alert-cooldown`)

When a `--until` condition fires, alert actions deliver notifications via webhooks, shell commands, or both. Available on `data`, `power`, and `export` commands.

```bash
# POST JSON payload to a webhook when solar export drops below threshold
homewizard-cli data --watch 5 \
  --until "active_power_w < -2000" \
  --alert-webhook https://hooks.slack.com/services/T00/B00/xxx

# Run a shell command when a condition fires
homewizard-cli power --watch 2 \
  --until "active_power_w > 5000" \
  --alert-cmd "mosquitto_pub -t home/alerts -m 'High power usage: $HW_CONDITION'"

# Prevent alert storms with cooldown (minimum seconds between dispatches)
homewizard-cli data --watch 10 \
  --until "active_power_w > 5000" \
  --alert-webhook https://ntfy.sh/my-topic \
  --alert-cooldown 300

# Chain multiple alert channels simultaneously
homewizard-cli data --watch 2 \
  --until "voltage_sag_l1_count != 0" \
  --alert-webhook https://hooks.slack.com/xxx \
  --alert-cmd "echo ALERT | systemd-cat -t homewizard" \
  --alert-cooldown 60
```

**Behavior:**

- **Without alerts:** `--until` exits with code 10 (unchanged behavior).
- **With alert actions in watch mode:** After dispatching alerts, polling continues instead of exiting. The same condition will re-trigger on the next poll (subject to cooldown).
- **With alert actions in one-shot mode (no `--watch`):** Alerts are dispatched, then the command exits with code 10.

**Webhook payload format:**

```json
{
  "timestamp": "2026-05-29T12:00:00+00:00",
  "condition": "active_power_w > 5000",
  "data": {
    "active_power_w": 5123.4,
    "total_power_import_kwh": 12345.6,
    ...
  }
}
```

**Shell command environment:** The triggering command receives:
- `HW_CONDITION` — The expression that fired (e.g. `"active_power_w > 5000"`)
- `HW_DATA` — JSON string of the full `DataResponse` dictionary

| Option              | Description                                                       |
|---------------------|-------------------------------------------------------------------|
| `--alert-webhook`   | URL to POST a JSON payload to when the condition fires             |
| `--alert-cmd`       | Shell command to execute when the condition fires                  |
| `--alert-cooldown`  | Minimum seconds between successive alert dispatches (default: 0)   |

---

## JSONPath Queries (`--query`)

Extract specific values using JSONPath syntax:

```bash
homewizard-cli data --query "$.active_power_w"
homewizard-cli data --query "$.total_power_import_kwh"
```

Works with `--format` — outputs as a Rich table for `table` format, JSON for all others.

---

## Delta Tracking (`--delta`)

With `--watch`, `--delta` shows only fields whose values have changed, with colored deltas:

```bash
homewizard-cli data --watch 2 --delta
homewizard-cli data --watch 2 --delta --fields active_power_w,total_power_import_kwh
```

```
┌─────────────────────┬─────────┬─────────┐
│ Field               │ Value   │ Delta   │
├─────────────────────┼─────────┼─────────┤
│ active_power_w      │ 456.789 │ +12.3   │
│ total_power_import  │ 12345.7 │ +0.001  │
└─────────────────────┴─────────┴─────────┘
```

Green deltas indicate increases, red indicates decreases. The `DeltaTracker` in `homewizard_cli/state.py` handles numeric field comparison and formatting.

---

## Template Output (`--template`)

Custom Go-style template syntax for arbitrary output:

```bash
homewizard-cli data --template "{{.active_power_w}}W | {{.total_power_import_kwh}}kWh"
homewizard-cli data --template "Power: {{.active_power_w}}W, Voltage: {{.active_voltage_l1_v}}V"
```

All `DataResponse` field names are available as template variables.

---

## Rate Limit Warning

Polling intervals below 1.0 second print a yellow warning:

```
Warning: Polling interval 0.5s is below recommended minimum (1.0s).
         Device may become unresponsive.
```

This applies to all commands that accept `--watch`.

---

## Configuration

Config file location: `~/.config/homewizard-cli/config.toml`

```toml
[default]
host = "192.168.1.100"
timeout = 5.0
format = "table"
timestamp_format = "%Y-%m-%d %H:%M:%S"

[export]
format = "influx"
watch = 10
file = "/var/log/homewizard/readings.log"
rotate = "daily"
broker = "mqtt://broker.local"
topic = "home/p1meter"
qos = 1
skip_unchanged = true
fields = "active_power_w,total_power_import_kwh"
delta = false
metrics_port = 9090
pid_file = "/var/run/hw-export.pid"
```

Export CLI options override config file values. Resolution order: CLI > config > hardcoded default.

---

## Shell Completions

```bash
homewizard-cli --install-completion     # install for current shell
homewizard-cli --show-completion        # show completion script
```

Supports bash, zsh, fish, and PowerShell.

---

## Error Handling

Typed error hierarchy with distinct exit codes:

| Exit Code | Error Type           | Description                            |
|-----------|----------------------|----------------------------------------|
| 1         | `P1Error` (generic)  | Unspecified error                      |
| 2         | `NotFoundError`      | Device not found / unreachable         |
| 3         | `HttpError`          | HTTP non-2xx response                  |
| 4         | `TimeoutError`       | Request timed out                      |
| 5         | `ParseError`         | Response parsing failed                |
| 6         | `CrcError`           | Telegram CRC mismatch                  |
| 7         | `WriteError`         | File/MQTT write failure                |
| 8         | `UnsupportedError`   | Device does not support this feature   |
| 10        | `SystemExit(10)`     | `--until` condition was met            |

Commands automatically detect device capabilities (e.g., `telegram` on a P1 Meter, `state` on an Energy Socket). If a command is invoked on a device that does not support it, the CLI exits with code **8** and prints an informative message.

All errors are caught at the entry point (`main.py`) and printed in red with their exit code.

---

## SSL Certificate Handling (v2)

The v2 client (HTTPS) handles SSL certificates as follows:

1. Loads the bundled HomeWizard CA certificate (if available in the package)
2. Looks for a user-provided CA certificate at `~/.config/homewizard-cli/homewizard-ca.pem`
3. If neither is present, uses the system's default CA store
4. `--no-verify` disables certificate verification entirely (useful for self-signed certs or development)

The bundled certificate enables `ssl.VERIFY_X509_PARTIAL_CHAIN` for proper chain validation.

**Hostname verification:** When a device identifier is available (from device info), the SSL context enables `hostname_checks_common_name` for proper hostname verification.

**`--no-verify` safety:** Using `--no-verify` without `--token` on API v2 is rejected with exit code 1, because v2 requires authentication and disabling verification without a token is almost always wrong. When `--no-verify` is used with a token, a warning is logged: "SSL verification disabled — connections are insecure."

---

## Proxy Support

Proxy resolution follows this priority chain:

1. Explicit `--proxy` CLI option (scheme://host:port)
2. `NO_PROXY` / `no_proxy` env var — exact host match (no wildcards), skips proxy
3. `HTTP_PROXY` / `HTTPS_PROXY` / `http_proxy` / `https_proxy` env vars

The `httpx.AsyncClient` respects standard `/etc/hosts` entries alongside proxy environment variables (`trust_env=False` is NOT set).

---

## systemd Service

For continuous logging and monitoring, run the export command as a systemd service. Create `/etc/systemd/system/homewizard-export.service`:

```ini
[Unit]
Description=HomeWizard P1 Meter data export
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=homewizard
ExecStart=homewizard-cli export \
    --watch 10 \
    --format influx \
    --file /var/log/homewizard/readings.log \
    --rotate daily \
    --metrics-port 9090 \
    --pid-file /run/homewizard-export.pid \
    --skip-unchanged
Restart=on-failure
RestartSec=5
PIDFile=/run/homewizard-export.pid
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now homewizard-export
journalctl -u homewizard-export -f     # tail logs
```

### Prometheus Scrape Config

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'homewizard'
    static_configs:
      - targets: ['localhost:9090']
```

---

## Development

```bash
# Clone and install
git clone https://github.com/SwordfishTrumpet/homewizard-cli
cd homewizard-cli
uv sync

# Lint (basic rules)
uv run ruff check homewizard_cli/ tests/

# Lint (extended rules — SIM, B, N, UP, I, C4)
uv run ruff check homewizard_cli/ tests/ --select E,W,F,I,UP,N,B,C4,SIM

# Typecheck (basic)
uv run python -m mypy homewizard_cli/ tests/

# Typecheck (full, including untyped defs)
uv run python -m mypy --check-untyped-defs homewizard_cli/ tests/

# Run tests
uv run python -m pytest tests/ -v

# Run tests with clean output (isolated processes — no warnings)
uv run python -m pytest tests/ --forked -v

# Run a single test file
uv run python -m pytest tests/test_commands.py -v

# Coverage
uv run python -m pytest tests/ --cov=homewizard_cli --cov-report=term-missing --cov-fail-under=90

# Install pre-commit hooks
uv run pre-commit install

# Run pre-commit hooks manually
uv run pre-commit run --all-files
```

Test fixtures live in `tests/fixtures/` (e.g., `api.json`, `data.json`, `system.json`). Mock patterns:

- **v1 commands:** Patch `homewizard_cli.commands.<cmd>.resolve_client` with `AsyncMock`, add `"--api-version", "v1"` to `runner.invoke()`
- **v2 commands:** Patch `homewizard_cli.commands.<cmd>.resolve_client`, mock `get_json_v2`
- **v2-only commands** (reboot, pair, users, batteries): Patch `homewizard_cli.commands.<cmd>.P1ClientV2` directly

---

## License

MIT — see the [GitHub repository](https://github.com/SwordfishTrumpet/homewizard-cli) for details.
