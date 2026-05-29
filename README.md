# homewizard-cli

High-performance CLI for HomeWizard P1 Meter, supporting both API v1 (HTTP, port 80) and API v2 (HTTPS, port 443, Bearer auth).

## Installation

```bash
pip install homewizard-cli                    # from PyPI
pip install homewizard-cli[ws]                # with WebSocket support
pip install homewizard-cli[dev]               # with development + optional deps
pip install git+https://github.com/anomalyco/homewizard-cli  # from source
```

Requires Python 3.11+ and a HomeWizard P1 Meter on the local network.

## Quick Start

```bash
# Show a summary of current power usage
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
# Show real-time power consumption
homewizard-cli power
```

```
456.8 W  (importing)
```

```bash
# Full data dump
homewizard-cli data
```

```
┌──────────────────────┬─────────────┐
│ Field                │ Value       │
├──────────────────────┼─────────────┤
│ active_power_w       │ 456.789     │
│ total_power_import   │ 12345.678   │
│ ...                  │             │
└──────────────────────┴─────────────┘
```

```bash
# Check if the device is reachable
homewizard-cli ping
```

```
P1 Meter at 192.168.1.100 — OK (42ms)
```

## Commands

### `data` — Full energy data

All fields from the P1 meter, with rich filtering and output control.

```bash
# One-shot dump
homewizard-cli data
```

Example output:

```
┌──────────────────────────────┬─────────────┐
│ Field                        │ Value       │
├──────────────────────────────┼─────────────┤
│ wifi_ssid                    │ MyNetwork   │
│ wifi_strength                │ 78          │
│ smr_version                  │ 50          │
│ meter_model                  │ SDM230      │
│ unique_id                    │ A1B2C3D4E5F6│
│ active_tariff                │ 1           │
│ total_power_import_kwh       │ 12345.678   │
│ total_power_import_t1_kwh    │ 8234.567    │
│ total_power_import_t2_kwh    │ 4111.111    │
│ total_power_export_kwh       │ 2345.678    │
│ total_power_export_t1_kwh    │ 1234.567    │
│ total_power_export_t2_kwh    │ 1111.111    │
│ active_power_w               │ 456.789     │
│ active_power_l1_w            │ 456.789     │
│ active_voltage_l1_v          │ 238.5       │
│ active_current_l1_a          │ 1.9         │
│ active_frequency_hz          │ 50.0        │
│ total_gas_m3                 │ 9876.543    │
│ gas_timestamp                │ 260529120000│
│ gas_unique_id                │ G1H2I3J4K5L6│
│ voltage_sag_l1_count         │ 2           │
│ voltage_swell_l1_count       │ 0           │
│ any_power_fail_count         │ 0           │
│ long_power_fail_count        │ 0           │
│ text_message                 │             │
│ active_power_average_w       │ 420.0       │
│ montly_power_peak_w          │ 3200.0      │
│ montly_power_peak_timestamp  │ 260528140000│
└──────────────────────────────┴─────────────┘
```

```bash

# Poll every 2 seconds
homewizard-cli data --watch 2

# Select specific fields
homewizard-cli data --fields active_power_w,active_voltage_l1_v,total_gas_m3

# Show only changed values (delta tracking)
homewizard-cli data --watch 2 --delta

# Custom template
homewizard-cli data --template "{{.active_power_w}}W | {{.total_power_import_kwh}}kWh"

# JSONPath query
homewizard-cli data --query "$.active_power_w"

# Exit when condition is met
homewizard-cli data --watch 1 --until "active_power_w > 1000"

# Real-time push via WebSocket (v2 only, requires websockets)
homewizard-cli data --ws
homewizard-cli data --ws --watch 10
homewizard-cli data --ws --until "active_power_w > 5000"
```

Options: `--watch`, `--fields`, `--template`, `--delta`, `--query`, `--until`, `--ws`, `--format`, `--proxy`

### `power` — Real-time power monitoring

Focused power readouts with optional sparkline trend.

```bash
# Simple one-shot
homewizard-cli power
```

Example output:

```
456.8 W  (importing)
```

```bash
homewizard-cli power --color
```

Example output:

```
456.8 W  (importing)
```

```bash
homewizard-cli power --sparkline
```

Example output:

```
456.8 W  (importing)
          ▃▃▄▄▅▆▇███▇▆▅▄▄▃▂▂▁▁
```

```bash
# Full details (import/export, voltage, current)
homewizard-cli power --full

# Color output (green=exporting, red=importing)
homewizard-cli power --color

# With sparkline trend (last 20 readings)
homewizard-cli power --sparkline

# Full + sparkline in watch mode
homewizard-cli power --full --sparkline --watch 1

# Watch until a condition
homewizard-cli power --watch --until "abs(active_power_w) > 2000"

# Machine-readable output
homewizard-cli power --format csv
```

Options: `--watch`, `--full`, `--color`, `--sparkline`, `--until`, `--format`, `--proxy`

### `power --full` example output

```
Net:      456.8 W
Import:     456.8 W
Export:      0.0 W
Voltage:  238.5 V
Current:    1.9 A
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

### `energy` — Cumulative energy readings

```bash
# Import/export/net totals
homewizard-cli energy

# With tariff breakdown (T1-T4)
homewizard-cli energy --tariffs
```

Options: `--tariffs`, `--proxy`

### `energy` example output

```
Import:  12,345.68 kWh
Export:   2,345.68 kWh
Net:     10,000.00 kWh consumed
```

With `--tariffs`:

```
Import:  12,345.68 kWh
Export:   2,345.68 kWh
Net:     10,000.00 kWh consumed

T1 (peak):     Import: 8,234.57  Export: 1,234.57
T2 (off-peak): Import: 4,111.11  Export: 1,111.11
```

### `gas` — Gas consumption

```bash
# Simple reading
homewizard-cli gas

# Full details (total, last read timestamp, meter ID)
homewizard-cli gas --full

# Watch mode
homewizard-cli gas --watch 10
```

Options: `--full`, `--watch`, `--proxy`

### `gas` example output

```
9,876.54 m³
```

With `--full`:

```
Total:     9,876.54 m³
Last read: 2026-05-29 12:00:00
Meter ID:  G1H2I3J4K5L6
```

### `quality` — Power quality

Voltage sags, swells, and power failure counters across up to 3 phases.

```bash
# All counters
homewizard-cli quality

# Alert mode — only print when counts change
homewizard-cli quality --watch --alert

# Show power failure event log (parsed from DSMR telegram)
homewizard-cli quality --events
```

Options: `--watch`, `--alert`, `--events`, `--proxy`

### `quality` example output

```
Voltage Sags L1: 2
Voltage Swells L1: 0
Voltage Sags L2: 1
Voltage Swells L2: 0
Short Failures:  0
Long Failures:   0
```

With `--events`:

```
Voltage Sags L1: 3
Voltage Swells L1: 0
Short Failures:  1
Long Failures:   0

Power Failure Events:
  2026-05-28 14:23:00 — Short outage (2 s)
```

### `telegram` — Raw DSMR telegram

Access the raw DSMR telegram for low-level diagnostics.

```bash
# Raw output
homewizard-cli telegram

# Validate CRC
homewizard-cli telegram --validate

# Parse into JSON
homewizard-cli telegram --format json

# Extract a specific OBIS code
homewizard-cli telegram --obis 1-0:1.8.1

# Explain what an OBIS code means
homewizard-cli telegram --explain 1-0:1.8.1

# Count telegrams per minute
homewizard-cli telegram --watch --rate
```

Options: `--validate`, `--obis`, `--explain`, `--watch`, `--rate`, `--format`, `--proxy`

### `telegram` example output (raw)

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

With `--format json`:

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

With `--validate`:

```
CRC: 522F — Valid
/XMX5LGBBFG123456789
...
!522F
```

With `--explain 1-0:1.8.1`:

```
1-0:1.8.1 — Total import energy (T1, peak)
```

### `info` — Device information

```bash
homewizard-cli info
```

Example output (v2):

```
Product:     P1 Meter
Type:        HWE-P1
Serial:      A1B2C3D4E
Firmware:    4.2.1
API:         v2
WiFi:        MyNetwork (-42 dBm)
Cloud:       enabled
```

Example output (v1):

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

Options: `--proxy`

### `system` — System settings

Read and modify device system settings.

```bash
# Read all v2 system settings
homewizard-cli system
```

Example output (v2):

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

# Set LED brightness (v2 only, 0-100)
homewizard-cli system --led-brightness 50

# v1 fallback
homewizard-cli system --api-version v1
homewizard-cli system --api-version v1 --cloud false
```

Options: `--cloud`, `--cloud-toggle`, `--led-brightness`, `--proxy`

### `identify` — Blink the LED

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

Options: `--count`, `--proxy`

### `ping` — Health check

Quick connectivity check with response time.

```bash
homewizard-cli ping
```

```
P1 Meter at 192.168.1.100 — OK (42ms)
```

```bash
homewizard-cli ping --quiet  # exit code only
```

Options: `--quiet`, `--proxy`

### `discover` — Network discovery

Discover HomeWizard devices on the local network via mDNS.

```bash
# Find the first device
homewizard-cli discover
```

Example output:

```
Found device at 192.168.1.100
```

```bash
# Verbose output with cache info
homewizard-cli discover --verbose
```

Example output:

```
Discovering P1 meter (timeout=3.0s) ...
Found device at 192.168.1.100
```

```bash
# Save discovered host to cache
homewizard-cli discover --save

# List ALL HomeWizard devices on the network
homewizard-cli discover --all
```

Example `--all` output:

```
┌───────────────┬──────────┬──────────┬──────────┐
│ IP            │ Product  │ Serial   │ Name     │
├───────────────┼──────────┼──────────┼──────────┤
│ 192.168.1.100 │ P1 Meter │ A1B2C3D4 │ P1 Meter │
│ 192.168.1.101 │ HWE-SG   │ E5F6G7H8 │ SmartPlug│
└───────────────┴──────────┴──────────┴──────────┘
```

Discovery uses `_homewizard._tcp.local.` (v2) first, then falls back to `_hwenergy._tcp.local.` (v1). Found hosts are cached for 24 hours.

### `dashboard` — Live Rich TUI

Full-screen real-time dashboard with Rich Layout/Live display.

```bash
homewizard-cli dashboard
homewizard-cli dashboard --watch 5
```

Renders a continuously updating full-screen layout:

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

Options: `--watch`, `--proxy`

### `export` — Machine-readable data streaming

Continuous export to file, MQTT, or stdout with rotation, metrics, and PID file support.

```bash
# Export to InfluxDB line protocol (default format)
homewizard-cli export --watch 10

# Export to CSV file
homewizard-cli export --format csv --file readings.csv --watch 60

# Export with daily file rotation
homewizard-cli export --format json --file p1.log --watch 60 --rotate daily

# Publish to MQTT
homewizard-cli export --format mqtt --broker mqtt://broker.local --topic home/p1meter --watch 30

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

Options: `--watch`, `--format`, `--file`, `--rotate` (daily|hourly), `--broker`, `--topic`, `--qos`, `--skip-unchanged`, `--fields`, `--delta`, `--until`, `--metrics-port`, `--pid-file`, `--proxy`

**Exponential backoff**: On fetch/write errors, retry with backoff starting at 1s, doubling up to 60s max. Backoff resets after a successful fetch.

**Signal handling**: Listens for SIGINT and SIGTERM for graceful shutdown — closes MQTT connections, flushes file handles, stops the metrics server, and removes the PID file.

**Metrics server** (`--metrics-port`): Exposes Prometheus-format metrics at `GET /metrics` with three counters: `homewizard_readings_total`, `homewizard_errors_total`, `homewizard_last_poll_timestamp_seconds`.

**PID file** (`--pid-file`): Writes PID on startup, removes on exit. Detects stale PIDs and existing running processes.

**File rotation** (`--rotate`): Supports `daily` (YYYY-MM-DD) and `hourly` (YYYY-MM-DDTHH) strategies. Previous file is renamed before a new one is opened.

### `serve` — HTTP proxy server (optional deps)

Start a FastAPI + uvicorn proxy server that forwards requests to the P1 meter. Requires `fastapi` and `uvicorn`.

```bash
homewizard-cli serve
homewizard-cli serve --port 9000 --cache 10
```

```bash
homewizard-cli serve
```

Example output:

```
P1 Meter at 192.168.1.100 — OK
Starting proxy at http://0.0.0.0:8000
Proxying to P1 Meter at 192.168.1.100
```

Then `curl http://localhost:8000/api/measurement` returns the device's JSON response.

Features:
- Proxies all `/api/*` paths to the P1 meter
- Optional response caching (in-memory, TTL in seconds)
- Supports both API v1 (HTTP) and v2 (HTTPS + Bearer auth)
- Validates device connectivity before starting

Options: `--bind`, `--port`, `--cache`, `--proxy`

### `reboot` — Reboot device (v2 only)

```bash
homewizard-cli reboot --token <token>
```

```
Reboot result: {"status": "ok"}
```

### `pair` — Create auth token (v2 only)

Press the physical button on the device within 30 seconds, then:

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

### `users` — Manage API users (v2 only)

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
# Delete a user
homewizard-cli users delete --name local/admin --token <token>
```

```
Deleted: {"status": "ok"}
```

### `batteries` — Plug-In Battery state (v2 only)

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

```bash
homewizard-cli batteries --mode zero --token <token>
homewizard-cli batteries --mode standby --token <token>
homewizard-cli batteries --mode predictive --token <token>
```

### `config` — Configuration management

```bash
# Validate config file
homewizard-cli config --validate
```

Config file at `~/.config/homewizard-cli/config.toml`:

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
skip_unchanged = true
metrics_port = 9090
pid_file = "/var/run/hw-export.pid"
```

## Output Formats

Available on most data commands via `--format`:

| Format      | Description                              |
|-------------|------------------------------------------|
| `table`     | Rich formatted table (default in TTY)    |
| `json`      | JSON object (default in pipes)           |
| `csv`       | Comma-separated values                   |
| `tsv`       | Tab-separated values                     |
| `influx`    | InfluxDB line protocol                   |
| `prometheus`| Prometheus exposition format             |
| `env`       | KEY=VALUE lines                          |
| `minimal`   | Tab-separated values (no header)         |
| `raw`       | Raw field:value pairs                    |
| `mqtt`      | MQTT publish (export command only)       |

## API Versioning

API v2 (HTTPS, port 443, Bearer auth) is the default. Use `--api-version v1` to fall back to v1 (HTTP, port 80, no auth).

```bash
homewizard-cli data                  # v2 (default)
homewizard-cli data --api-version v1 # v1 fallback
homewizard-cli info --token MY_TOKEN
homewizard-cli info --token MY_TOKEN --no-verify
```

### API v1 ↔ v2 mapping

| Feature      | v1                                  | v2                                   |
|--------------|-------------------------─────-------|-------------------------------──---─-|
| Protocol     | HTTP (port 80)                      | HTTPS (port 443)                     |
| Auth         | None                                | Bearer token                         |
| Data         | `/api/v1/data` → `DataResponse`     | `/api/measurement` → `MeasurementV2` |
| System       | `/api/v1/system` → `SystemResponse` | `/api/system` → `SystemV2`           |
| Discovery    | `_hwenergy._tcp.local.`             | `_homewizard._tcp.local.`            |

v2-only commands: `reboot`, `pair`, `users list`, `users delete`, `batteries`

v2 measurement data is automatically converted to v1 format for compatibility with all formatters.

## Global Options

| Option           | Description                          |
|------------------|--------------------------------------|
| `--host, -H`     | P1 meter IP address                  |
| `--timeout, -t`  | HTTP request timeout (default: 3s)   |
| `--proxy`        | HTTP proxy URL                       |
| `--format, -f`   | Output format                        |
| `--no-color`     | Disable ANSI colors                  |
| `--quiet, -q`    | Suppress non-error output            |
| `--verbose, -v`  | Show HTTP request details            |
| `--api-version`  | API version: v1 or v2 (default: v2)  |
| `--token`        | API v2 Bearer token                  |
| `--no-verify`    | Disable SSL cert verification (v2)   |
| `--version`      | Show version and exit                |

Host resolution priority: CLI `--host` > config file `[default].host` > `192.168.68.109`

## Host Discovery

`homewizard-cli discover` automatically finds your P1 meter via mDNS:
1. Queries `_homewizard._tcp.local.` (v2 devices)
2. Falls back to `_hwenergy._tcp.local.` (v1 legacy devices)
3. Falls back to ARP table scan (checks MAC prefixes `5c:62:8b` and `3c:61:05` in `/proc/net/arp`)
4. Caches the result for 24 hours

## WebSocket Support

The `data --ws` option uses WebSocket push (v2 only) instead of HTTP polling. Requires the optional `websockets` package:

```bash
pip install homewizard-cli[ws]
homewizard-cli data --ws
homewizard-cli data --ws --watch 10
```

Without `--watch`, a single message is received and the connection closes.

## Expression Conditions (`--until`)

Exit when a numeric field crosses a threshold:

```bash
--until "active_power_w > 1000"
--until "total_power_import_kwh >= 5000"
--until "abs(active_power_w) < 10"
--until "voltage_sag_l1_count != 0"
```

Supports `>`, `<`, `>=`, `<=`, `==`, `!=`, and `abs()` wrapping.

## JSONPath Queries (`--query`)

Extract specific values using JSONPath syntax:

```bash
homewizard-cli data --query "$.active_power_w"
homewizard-cli data --query "$.total_power_import_kwh"
```

## Delta Tracking (`--delta`)

With `--watch`, only show fields whose values have changed, with green/red colored deltas:

```bash
homewizard-cli data --watch 2 --delta
homewizard-cli data --watch 2 --delta --fields active_power_w,total_power_import_kwh
```

## Template Output (`--template`)

Custom Go-style template syntax:

```bash
homewizard-cli data --template "{{.active_power_w}}W | {{.total_power_import_kwh}}kWh"
homewizard-cli data --template "Power: {{.active_power_w}}W, Voltage: {{.active_voltage_l1_v}}V"
```

## Rate Limit Warning

Polling intervals below 1.0s print a yellow warning:

```
Warning: Polling interval 0.5s is below recommended minimum (1.0s).
         Device may become unresponsive.
```

## Configuration

Config file: `~/.config/homewizard-cli/config.toml`

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
skip_unchanged = true
```

## Shell Completions

```bash
homewizard-cli --install-completion  # install for current shell
homewizard-cli --show-completion     # show completion script
```

## Error Handling

Typed error hierarchy with distinct exit codes:

| Exit Code | Error Type              |
|-----------|--------------------────-|
| 1         | Generic error           |
| 2         | Device not found        |
| 3         | HTTP error              |
| 4         | Timeout                 |
| 5         | Parse error             |
| 6         | CRC mismatch            |
| 7         | Write error             |
| 10        | `--until` condition met |

## SSL Certificate Handling (v2)

The client looks for a CA certificate at `~/.config/homewizard-cli/homewizard-ca.pem`. If absent, the system's default CA store is used. Pass `--no-verify` to skip certificate verification entirely.

## Development

```bash
uv sync                    # install dependencies
uv run ruff check .        # lint
uv run python -m mypy --check-untyped-defs .  # typecheck
uv run python -m pytest tests/ -v  # run tests (425+ tests)
```

## Proxy Support

Proxy resolution priority: explicit `--proxy` > `NO_PROXY`/`no_proxy` (exact match, no wildcards) > `HTTP_PROXY`/`HTTPS_PROXY` (uppercase and lowercase).

## systemd Service

For continuous logging, run the export command as a systemd service. Create `/etc/systemd/system/homewizard-export.service`:

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
journalctl -u homewizard-export -f  # tail logs
```

The service uses `--pid-file` for double-start protection, `--rotate daily` for log management, `--skip-unchanged` to reduce writes, and `--metrics-port` for Prometheus scraping.

### Prometheus scraping target

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'homewizard'
    static_configs:
      - targets: ['localhost:9090']
```

## License

MIT
