# homewizard-cli

A command-line tool for the HomeWizard P1 Meter. It reads the meter over your local network —
live power, cumulative energy and gas, power quality, and the raw DSMR telegram — and can log,
export, price, serve or display those readings without a cloud account.

It speaks both meter APIs: v2 over HTTPS with a Bearer token, and the older v1 over plain HTTP.
The first screen tells you what to do first; the reference at the back lists every flag.

## Contents

**Part I — Welcome**
- [1. What this is](#1-what-this-is)
- [2. What a run looks like](#2-what-a-run-looks-like)
- [3. The two API versions](#3-the-two-api-versions)

**Part II — Getting started**
- [4. Requirements](#4-requirements)
- [5. Install](#5-install)
- [6. Find your meter](#6-find-your-meter)
- [7. Read your first values](#7-read-your-first-values)

**Part III — Concepts**
- [8. Output formats](#8-output-formats)
- [9. The measurement model](#9-the-measurement-model)
- [10. Watch mode](#10-watch-mode)
- [11. Conditions and alerts](#11-conditions-and-alerts)
- [12. The configuration file](#12-the-configuration-file)

**Part IV — Guides**
- [13. Read power energy gas and water](#13-read-power-energy-gas-and-water)
- [14. Inspect power quality](#14-inspect-power-quality)
- [15. Read the raw telegram](#15-read-the-raw-telegram)
- [16. Keep a history](#16-keep-a-history)
- [17. Work out what a period costs](#17-work-out-what-a-period-costs)
- [18. Export readings](#18-export-readings)
- [19. Serve a REST proxy](#19-serve-a-rest-proxy)
- [20. Feed Home Assistant](#20-feed-home-assistant)
- [21. Manage the device](#21-manage-the-device)
- [22. Watch it on a dashboard](#22-watch-it-on-a-dashboard)
- [23. Fetch everything at once](#23-fetch-everything-at-once)

**Part V — Reference**
- [24. Global options](#24-global-options)
- [25. Command reference](#25-command-reference)
- [26. Exit codes](#26-exit-codes)
- [27. Files and environment](#27-files-and-environment)

**Part VI — Operations**
- [28. Run it unattended](#28-run-it-unattended)
- [29. Scrape the metrics endpoint](#29-scrape-the-metrics-endpoint)
- [30. Stream over a WebSocket](#30-stream-over-a-websocket)
- [31. Route through a proxy](#31-route-through-a-proxy)
- [32. Certificates on API v2](#32-certificates-on-api-v2)
- [33. Keep the poll rate sane](#33-keep-the-poll-rate-sane)

**Part VII — The project**
- [34. Status and limits](#34-status-and-limits)
- [35. Development](#35-development)
- [36. License](#36-license)

# Part I: Welcome

## 1. What this is

The HomeWizard P1 Meter sits between your electricity meter and your network. It serves one JSON
reading at a time, plus a raw DSMR telegram, over your LAN. This CLI is a client for that device:
it asks once, prints the answer in the shape you asked for, and exits.

What you can do with it, in one line each:

| Want | Command |
|---|---|
| Current power, in watts | `homewizard-cli power` |
| Every field the meter exposes | `homewizard-cli data` |
| Cumulative energy, with tariff split | `homewizard-cli energy --tariffs` |
| Gas or water totals | `homewizard-cli gas`, `homewizard-cli water` |
| Voltage sags, swells, outages | `homewizard-cli quality` |
| The raw DSMR telegram, with CRC check | `homewizard-cli telegram --validate` |
| A stream into InfluxDB, MQTT or Prometheus | `homewizard-cli export` |
| A SQLite archive you can query later | `--db` on any read, then `homewizard-cli history` |
| What a day of energy cost | `homewizard-cli cost --today` |
| A REST proxy in front of the meter | `homewizard-cli serve` |
| Home Assistant sensors | `homewizard-cli hass` |
| Device settings, battery mode, reboot | `homewizard-cli system`, `batteries`, `reboot` |

It is a single-shot tool by default: one HTTP request per command, then exit. Long-running work is
opt-in: `--watch`, `export`, `serve`, `dashboard`.

## 2. What a run looks like

Every command follows the same three steps, which is why the flags repeat across commands:

1. **Resolve a host.** `--host`, or the one in your config file, or the one `discover` cached.
2. **Make one request** (or poll on an interval when you asked to watch).
3. **Write the answer** in the format you asked for — a table on a terminal, JSON when piped.

```bash
homewizard-cli power
```

```
456.8 W  (importing)
```

```bash
homewizard-cli power --format json
```

```json
{"active_power_w": 456.789, "active_tariff": 1, "total_power_import_kwh": 12345.678}
```

The same reading, three ways: a human line, a table, or JSON. Chapter 8 covers the full set.

## 3. The two API versions

API v2 (HTTPS, port 443, Bearer token) is the default. `--api-version v1` switches to the older
HTTP API on port 80, which needs no token. Any other value is refused with exit code 2 instead of
quietly falling back to v1.

```bash
homewizard-cli data                    # v2, the default
homewizard-cli data --api-version v1   # v1 fallback

homewizard-cli info --token MY_TOKEN
homewizard-cli info --token MY_TOKEN --no-verify
```

| Piece | v1 | v2 |
|---|---|---|
| Protocol | HTTP, port 80 | HTTPS, port 443 |
| Auth | none | optional Bearer token |
| Client class | `P1Client` | `P1ClientV2` |
| Data endpoint | `/api/v1/data` | `/api/measurement` |
| System endpoint | `/api/v1/system` | `/api/system` |
| Device info | `/api/` | `/api` |
| Identify | `PUT /api/v1/identify` | `PUT /api/system/identify` |
| Telegram | `GET /api/v1/telegram` | `GET /api/telegram` |
| mDNS service | `_hwenergy._tcp.local.` | `_homewizard._tcp.local.` |

Six commands have no v1 equivalent and only work on v2: `reboot`, `pair`, `users list`,
`users delete`, `batteries`, and `state` with a write flag.

# Part II: Getting started

## 4. Requirements

- **Python 3.11 or later.**
- A HomeWizard P1 Meter and a Wi-Fi network it is reachable on. The CLI never talks to a cloud
  service.
- API v2 needs a token, which you create once by pressing the device button (`homewizard-cli pair`,
  chapter 21). API v1 needs nothing.

```bash
python3 --version
```

```
Python 3.11.9
```

## 5. Install

```bash
pip install homewizard-cli
```

```bash
homewizard-cli --version
```

```
homewizard-cli v0.4.0 (Python 3.11.9, Linux x86_64)
```

Optional extras, only for the features that need them:

```bash
pip install "homewizard-cli[ws]"     # data --ws (WebSocket push)
pip install "homewizard-cli[dev]"    # every optional dependency, plus the test tools
```

From a checkout, when you want the source rather than a release:

```bash
pip install git+https://github.com/SwordfishTrumpet/homewizard-cli
```

The repository also documents how to build and run it from a clone in chapter 35.

## 6. Find your meter

You need its address once. `discover` finds it and can remember it:

```bash
homewizard-cli discover
```

```
Found device at 192.168.1.100
```

```bash
homewizard-cli discover --save      # remember it in ~/.config/homewizard-cli/host for 24 hours
homewizard-cli discover --verbose   # show the mDNS query and cache state
homewizard-cli discover --all       # every HomeWizard device on the network
```

```
┌───────────────┬──────────┬──────────┬──────────┐
│ IP            │ Product  │ Serial   │ Name     │
├───────────────┼──────────┼──────────┼──────────┤
│ 192.168.1.100 │ P1 Meter │ A1B2C3D4 │ P1 Meter │
│ 192.168.1.101 │ HWE-SG   │ E5F6G7H8 │ SmartPlug│
└───────────────┴──────────┴──────────┴──────────┘
```

Discovery tries four things in order:

1. `_homewizard._tcp.local.` — the v2 mDNS service.
2. `_hwenergy._tcp.local.` — the v1 legacy service.
3. An ARP scan of `/proc/net/arp`, looking for HomeWizard MAC prefixes `5c:62:8b` and `3c:61:05`.
4. The cache at `~/.config/homewizard-cli/host`, valid for 24 hours.

| Option | What it does |
|---|---|
| `--save` | Persist the discovered host to the cache |
| `--all` | List every HomeWizard device instead of the first |
| `--verbose` | Show mDNS progress and whether the answer came from cache |

Once you know the address, confirm you can reach it and ask the device who it is:

```bash
homewizard-cli ping --host 192.168.1.100
```

```
P1 Meter at 192.168.1.100 — OK (42ms)
```

```bash
homewizard-cli info --host 192.168.1.100 --token MY_TOKEN
```

```
Product:     P1 Meter
Type:        HWE-P1
Serial:      A1B2C3D4E
Firmware:    4.2.1
API:         v2
WiFi:        MyNetwork (-42 dBm)
Cloud:       enabled
```

On v1 the same command reports the Wi-Fi percentage and the meter model instead of the RSSI and
cloud state. `ping --quiet` prints nothing and only sets the exit code, which is what a cron job
wants.

## 7. Read your first values

With a host configured, the bare command prints the fields that matter:

```bash
homewizard-cli
```

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

Everything the meter knows is one command away:

```bash
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

Narrow it to the fields you care about, in either shape:

```bash
homewizard-cli data --fields active_power_w,active_voltage_l1_v,total_gas_m3
homewizard-cli data --fields active_power_w --format json
```

Nothing is configured yet? Put the host in the config file once, and every later command finds it
(chapter 12).

# Part III: Concepts

## 8. Output formats

Most read commands take `--format`. The choice controls the shape of the same reading.

| Format | Output | Use it for |
|---|---|---|
| `table` | Rich table | Reading at a terminal |
| `json` | one JSON object | Scripts, `jq` |
| `csv` | comma-separated, header row | Spreadsheets, imports |
| `tsv` | tab-separated, header row | `cut`, `awk` |
| `influx` | InfluxDB line protocol | InfluxDB writes |
| `prometheus` | exposition format | A scrape or a textfile collector |
| `env` | `export KEY=value` lines | Shell environments |
| `minimal` | one pipe-separated line | A prompt or a status bar |
| `raw` | `field:value` pairs | Eyeballing a single reading |
| `mqtt` | an MQTT publish | `export` only, needs `--broker` |

`auto`, the default, picks `table` on an interactive terminal and `json` when the output is piped.
A format can also come from the config file (chapter 12).

CSV and TSV rows start with a `timestamp` column: the meter's own reading time when the API
reports one, otherwise the moment the row was written. Both carry a UTC offset so the value names
one instant, including across a daylight-saving change. Their column order is timestamp, total
power, L1, L2, L3, voltage L1–L3, frequency, import, export, gas.

Two more ways to reshape a reading without changing the format:

```bash
homewizard-cli data --query "$.active_power_w"          # JSONPath: one value out
homewizard-cli data --template "{{.active_power_w}}W"   # Go-style template
```

`--query` accepts a JSONPath expression or a bare field name, and returns JSON (or a table, when
the format is `table`). `--template` has every field of the reading available as `{{.name}}`:

```bash
homewizard-cli data --template "Power: {{.active_power_w}}W, Voltage: {{.active_voltage_l1_v}}V"
```

```
Power: 456.789W, Voltage: 238.5V
```

## 9. The measurement model

All commands, both API versions, hand you the same field names. The v2 payload is mapped onto the
v1 names when it is read, so a script written against v1 keeps working on v2.

| Field group | Names |
|---|---|
| Power | `active_power_w`, `active_power_l1_w`, `active_power_l2_w`, `active_power_l3_w`, `active_power_average_w`, `monthly_power_peak_w` |
| Energy totals | `total_power_import_kwh`, `total_power_export_kwh`, and `_t1_` through `_t4_` variants |
| Voltage and current | `active_voltage_l1_v`–`l3`, `active_current_a`, `active_current_l1_a`–`l3` |
| Quality | `voltage_sag_l1_count`–`l3`, `voltage_swell_l1_count`–`l3`, `any_power_fail_count`, `long_power_fail_count` |
| Gas | `total_gas_m3`, `gas_timestamp`, `gas_unique_id` |
| Identity | `meter_model`, `unique_id`, `smr_version`, `active_tariff`, `wifi_ssid`, `wifi_strength` |
| Time | `timestamp` |
| Sub-meters | `external[]`, each with `unique_id`, `type`, `timestamp`, `value`, `unit` |

Three things to know:

- **Optional fields stay optional.** A single-phase meter has no `active_power_l2_w`; a meter
  without a gas module has no `total_gas_m3`. Those keys are `null`, not zero, and the formats
  leave them empty.
- **`timestamp` is the reading time.** API v2 reports it; v1 does not, so it stays empty and CSV
  and TSV fall back to the moment of the export. `--format raw` writes it as the DSMR
  `0-0:1.0.0(...)` line.
- **`external` carries sub-meters.** Water and heat readings live there, and gas appears both as
  a flat `total_gas_m3` and as an `external` entry.

## 10. Watch mode

`--watch <seconds>` turns a one-shot read into a polling loop that prints each result:

```bash
homewizard-cli data --watch 5     # every 5 seconds
homewizard-cli power --watch 1    # every second
homewizard-cli gas --watch 10     # every 10 seconds
```

Every command that watches needs the interval; `dashboard` is the one command with a default
(2 seconds). There is no implicit polling — leave `--watch` off and the command reads once and
exits. Press Ctrl+C to stop, or use a condition (chapter 11).

Flags that only make sense while watching:

| Flag | Effect |
|---|---|
| `--delta` | Print only fields whose value changed, with green/red deltas |
| `--sparkline` | (`power`) a 20-sample trend line: `▁▂▃▄▅▆▇█` |
| `--agg` | Rolling mean, min, max and standard deviation, from the second sample on |
| `--alert` | (`quality`) print only when a sag or swell counter changes |
| `--rate` | (`telegram`) count telegrams per minute |
| `--skip-unchanged` | (`export`) skip writes when nothing changed |

```bash
homewizard-cli data --watch 2 --delta
```

```
┌─────────────────────┬─────────┬─────────┐
│ Field               │ Value   │ Delta   │
├─────────────────────┼─────────┼─────────┤
│ active_power_w      │ 456.789 │ +12.3   │
│ total_power_import  │ 12345.7 │ +0.001  │
└─────────────────────┴─────────┴─────────┘
```

`--agg` on `data` and `export` adds a `{field}_mean`, `{field}_min`, `{field}_max` and
`{field}_stddev` for each numeric field it has seen at least twice; `power --agg` prints a single
summary line. Chapter 33 covers how fast you may poll.

## 11. Conditions and alerts

`--until` makes a loop stop by itself. It takes a comparison on a numeric field:

```bash
--until "active_power_w > 1000"
--until "total_power_import_kwh >= 5000"
--until "abs(active_power_w) < 10"
--until "voltage_sag_l1_count != 0"
--until "active_voltage_l1_v <= 220"
```

Operators are `>`, `<`, `>=`, `<=`, `==` and `!=`. `AND`, `OR` and `NOT` combine comparisons, and
`abs()` and parentheses work inside them:

```bash
homewizard-cli data --watch 1 --until "active_power_w > 1000 AND total_gas_m3 < 10"
```

The command exits with code 10 when the condition is met.

Attach an alert and the loop keeps going after it fires, so one threshold can page you repeatedly
instead of ending the run:

```bash
homewizard-cli data --watch 5 \
  --until "active_power_w < -2000" \
  --alert-webhook https://ntfy.sh/my-topic \
  --alert-cooldown 300
```

| Flag | What it does |
|---|---|
| `--alert-webhook` | POST a JSON payload to this URL when the condition fires |
| `--alert-cmd` | Run this shell command when the condition fires |
| `--alert-cooldown` | Minimum seconds between two dispatches (default: 0) |

The webhook receives the condition, the time, and the whole reading:

```json
{
  "timestamp": "2026-05-29T12:00:00+00:00",
  "condition": "active_power_w > 5000",
  "data": {"active_power_w": 5123.4, "total_power_import_kwh": 12345.6}
}
```

`--alert-cmd` runs with two environment variables: `HW_CONDITION`, the expression that fired, and
`HW_DATA`, the full reading as JSON.

```bash
homewizard-cli power --watch 2 \
  --until "active_power_w > 5000" \
  --alert-cmd "mosquitto_pub -t home/alerts -m \"\$HW_CONDITION\""
```

Without an alert flag, `--until` simply exits (code 10). With one, in watch mode, the loop
continues; without `--watch`, it dispatches once and then exits with code 10.

## 12. The configuration file

Anything you would rather not retype goes in `~/.config/homewizard-cli/config.toml`:

```toml
[default]
host = "192.168.1.100"
timeout = 5.0
format = "table"
timestamp_format = "%Y-%m-%d %H:%M:%S"
token = "your-v2-token"
no_verify = false

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

[tariffs]
t1_rate = 0.30
t2_rate = 0.20
export_credit = 0.10
currency = "EUR"
```

Every value resolves CLI > config file > built-in default. `[default]` applies to subcommands as
well: `host`, `timeout`, `format`, `token` and `no_verify` are used when the command itself did not
get the matching flag, so `timeout = 10.0` reaches `homewizard-cli data` and not only the bare
command. `[export]` keys are read by `export`, and `[tariffs]` keys by `cost`.

Two things the file is strict about:

- **Types are checked.** `no_verify`, `skip_unchanged` and `delta` must be unquoted TOML booleans.
  A quoted `"false"` is ignored, because read as text it would be true and would switch TLS
  verification off. `timeout` and `watch` must be numbers, `qos` and `metrics_port` whole numbers,
  and the rates numbers. A value of the wrong type is ignored with a warning on stderr.
- **A syntax error is reported, not swallowed.** A file that cannot be parsed is named where it
  was needed, with the line: `Invalid TOML in ...: Expected newline ... (at line 3, column 15)`.

Check the file without touching the meter:

```bash
homewizard-cli config --validate
homewizard-cli config --show
```

# Part IV: Guides

## 13. Read power energy gas and water

### `data` — everything

The full reading, with the filtering flags from chapters 8 and 10.

```bash
homewizard-cli data
homewizard-cli data --watch 2
homewizard-cli data --fields active_power_w,active_voltage_l1_v,total_gas_m3
homewizard-cli data --watch 2 --delta
homewizard-cli data --format csv
```

| Option | What it does |
|---|---|
| `--fields a,b` | Print only these fields |
| `--watch N` | Poll every N seconds |
| `--delta` | Only changed fields, with deltas (needs `--watch`) |
| `--agg` | Rolling statistics while watching |
| `--query EXPR` | JSONPath or bare field name |
| `--template TEXT` | Go-style template |
| `--until EXPR` | Stop when the condition holds |
| `--ws` | WebSocket push instead of polling (chapter 30) |
| `--alert-webhook`, `--alert-cmd`, `--alert-cooldown` | Actions on `--until` (chapter 11) |
| `--db` | Log each reading to SQLite (chapter 16) |
| `--format` | Any format from chapter 8 |

### `power` — just the watts

```bash
homewizard-cli power
```

```
456.8 W  (importing)
```

```bash
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
homewizard-cli power --full --sparkline --watch 1
```

```
Net:      456.8 W
Import:     456.8 W
Export:      0.0 W
Voltage:  238.5 V
Current:    1.9 A
Trend:    ▃▃▄▄▅▆▇███▇▆▅▄▄▃▂▂▁▁
```

| Option | What it does |
|---|---|
| `--full` | Import/export split, voltage, current |
| `--color` | Green while exporting, red while importing |
| `--sparkline` | Last 20 readings as a trend line |
| `--agg` | One-line rolling statistics while watching |
| `--watch` | Poll interval in seconds |

### `energy` — cumulative kWh

```bash
homewizard-cli energy --tariffs
```

```
Import:  12,345.68 kWh
Export:   2,345.68 kWh
Net:     10,000.00 kWh consumed

T1 (peak):     Import: 8,234.57  Export: 1,234.57
T2 (off-peak): Import: 4,111.11  Export: 1,111.11
```

T3 and T4 lines appear only when the meter exposes those counters.

### `gas` and `water`

```bash
homewizard-cli gas --full
```

```
Total:     9,876.54 m³
Last read: 2026-05-29 12:00:00
Meter ID:  G1H2I3J4K5L6
```

```bash
homewizard-cli water --full
```

```
Total:     1,234.56 m³
Last read: 2026-05-29 12:00:00
Meter ID:  W1A2T3E4R5
```

Both accept `--watch` for a loop. Water readings come from the meter's sub-meter list, so a device
without a water module has nothing to show. Gas appears both as a flat total and as a sub-meter.

## 14. Inspect power quality

Sag, swell and outage counters, per phase when the meter has three:

```bash
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
homewizard-cli quality --watch 60 --alert    # print only when a counter moves
homewizard-cli quality --events              # the outage log from the telegram
```

```
Voltage Sags L1: 3
Voltage Swells L1: 0
Short Failures:  1
Long Failures:   0

Power Failure Events:
  2026-05-28 14:23:00 - Short outage (2 s)
```

| Option | What it does |
|---|---|
| `--alert` | Only print when a counter changes (needs `--watch`) |
| `--events` | The parsed power-failure log |
| `--watch` | Poll interval in seconds |

## 15. Read the raw telegram

The DSMR telegram is what the meter actually says, byte for byte. Useful when a field looks wrong
or you are comparing against another reader.

```bash
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
homewizard-cli telegram --validate
```

```
CRC: 522F (Valid)
```

The checksum covers the telegram up to and including the `!`, with the original CRLF line endings.
A reader that normalises line endings to LF will compute a different value and report a valid
telegram as broken; that is a property of the format, not of your meter.

Parse it instead of reading it:

```bash
homewizard-cli telegram --format json
```

```json
{
  "header": "/XMX5LGBBFG123456789",
  "timestamp": "260529120000W",
  "obis": {
    "1-0:1.8.1": "00012345.678*kWh",
    "1-0:1.7.0": "000456.789*kW"
  },
  "crc": "522F",
  "valid": true
}
```

`--named` replaces the codes with their meanings, `--obis CODE` extracts one value, and
`--explain CODE` tells you what a code means:

```bash
homewizard-cli telegram --obis 1-0:1.8.1
homewizard-cli telegram --explain 1-0:1.8.1
```

```
1-0:1.8.1 - Total import energy (T1, peak)
```

| Option | What it does |
|---|---|
| `--validate` | Check the CRC |
| `--obis CODE` | Print the value of one OBIS code |
| `--explain CODE` | Describe an OBIS code |
| `--named` | Use human-readable names in JSON output |
| `--rate` | Count telegrams per minute (needs `--watch`) |
| `--format` | `json`, `table`, `csv`, `tsv`, `raw` |

## 16. Keep a history

The meter keeps totals; it does not keep a time series. This CLI can: add `--db` to a read and
every sample is appended to a SQLite file.

```bash
homewizard-cli export --watch 10 --db ~/.config/homewizard-cli/energy.db
homewizard-cli data --db ~/.config/homewizard-cli/energy.db
```

`--db` works on `data`, `power`, `energy`, `gas`, `water`, `combined`, `dashboard` and `export`.
The default path is `~/.config/homewizard-cli/energy.db`, and `HW_DB` overrides it.

Query the archive with `history`. It reads the file only; it never contacts the meter.

```bash
homewizard-cli history --info
```

```
Database:    ~/.config/homewizard-cli/energy.db
Size:        4.2 MB
Rows:        87,402
Devices:     1 (ABC123, P1 Meter)
Date range:  2026-03-14 08:00:00 .. 2026-05-29 14:32:00
Completeness: 94.3%
```

```bash
# Yesterday, one row per hour
homewizard-cli history --yesterday --agg hourly --fields active_power_w

# This month, one row per day, as CSV
homewizard-cli history --this-month --agg daily \
  --fields total_power_import_kwh,total_power_export_kwh --format csv

# This week against last week
homewizard-cli history --this-week --compare last-week \
  --fields active_power_w,total_power_import_kwh

# Peaks and troughs
homewizard-cli history --this-month --top 5 --fields active_power_w
homewizard-cli history --this-month --bottom 5 --fields total_gas_m3

# What was logged while the exporter was down
homewizard-cli history --since-last --agg daily --fields total_power_import_kwh

# Several devices in one file
homewizard-cli history --list-devices
homewizard-cli history --device-id ABC123 --yesterday --agg hourly --fields active_power_w

# Reclaim disk space
homewizard-cli history --vacuum
```

| Option | What it selects |
|---|---|
| `--today`, `--yesterday` | The calendar day |
| `--this-week`, `--this-month` | Monday 00:00, or the 1st, to now |
| `--range A..B` | An arbitrary range, e.g. `"2026-05-01..2026-05-29"` |
| `--since-last` | From the newest stored row to now |
| `--compare last-week\|last-month\|last-year` | The same window, one step back |
| `--top N`, `--bottom N` | The N highest or lowest rows |
| `--fields a,b` | Columns to select |
| `--device-id SERIAL` | One device from the file |
| `--list-devices` | Every device serial in the file |
| `--agg hourly\|daily\|weekly\|monthly` | Group into periods |
| `--info` | File metadata and completeness |
| `--vacuum` | Compact the file |
| `--format` | `table`, `json`, `csv`, `tsv` |
| `--db` | The SQLite file to read (default `~/.config/homewizard-cli/energy.db`, or `HW_DB`) |

Readings are committed in batches, so a second process reading the same file sees new rows after
the writer closes, prunes or vacuums. `export --retain-days N` prunes automatically and refuses
`N < 1` rather than emptying the table.

`--format csv` and `--format tsv` are meant for other programs: numbers come out without thousands
separators, an absent value is an empty field rather than a dash, and TSV keeps its tabs. Use
`--format json` when you want the values typed instead of rendered.

## 17. Work out what a period costs

`cost` multiplies the meter's counters by the rates you give it.

```bash
homewizard-cli cost                     # from the current reading
homewizard-cli cost --tariffs           # with the per-tariff table
homewizard-cli cost --watch 30          # a live ticker
```

```
Current Cost Breakdown:
┌─────────────┬──────────┬───────┬──────────┐
│ Tariff      │ kWh      │ Rate  │ Cost     │
├─────────────┼──────────┼───────┼──────────┤
│ T1 (peak)   │ 8,234.57 │ 0.30€ │ 2,470.37€ │
│ T2 (off-peak│ 4,111.11 │ 0.20€ │ 822.22€  │
│ Export      │ 2,345.68 │ 0.10€ │ -234.57€ │
├─────────────┼──────────┼───────┼──────────┤
│ Total       │          │       │ 3,058.02€ │
└─────────────┴──────────┴───────┴──────────┘
```

Over a period, read the counters out of the history file instead:

```bash
homewizard-cli cost --today      --db ~/.config/homewizard-cli/energy.db
homewizard-cli cost --yesterday  --db ~/.config/homewizard-cli/energy.db
homewizard-cli cost --this-month --db ~/.config/homewizard-cli/energy.db

# rates on the command line, for a one-off
homewizard-cli cost --t1-rate 0.35 --t2-rate 0.25 --currency USD
```

The period cost sums each tariff's own counter, so a day that used both peak and off-peak energy is
priced per tariff rather than at whichever tariff happened to be active at the end. A reading that
carries no tariff counters is priced at the active tariff, because the data does not say how the
total splits. Export credit applies to the export delta.

| Option | What it sets |
|---|---|
| `--tariffs` | Print the per-tariff table |
| `--today`, `--yesterday`, `--this-month` | The period to price from the history file |
| `--db` | The SQLite file (default `~/.config/homewizard-cli/energy.db`) |
| `--t1-rate` … `--t4-rate` | Rate per tariff, in currency per kWh |
| `--export-credit` | Credit per exported kWh |
| `--currency` | Currency label (default `EUR`) |
| `--watch` | Recalculate on an interval |

Rates can live in the config file under `[tariffs]` (chapter 12) instead of on the command line.

## 18. Export readings

`export` is the loop that writes somewhere on an interval: a file, an MQTT topic, or stdout.

```bash
homewizard-cli export --watch 10
homewizard-cli export --format csv --file readings.csv --watch 60
homewizard-cli export --format json --file p1.log --watch 60 --rotate daily
homewizard-cli export --format json --file readings.log --watch 30 --rotate hourly
homewizard-cli export --format mqtt --broker mqtt://broker.local --topic home/p1meter --watch 30
homewizard-cli export --watch 10 --metrics-port 9090
homewizard-cli export --watch 10 --pid-file /var/run/hw-export.pid
homewizard-cli export --watch 10 --db ~/.config/homewizard-cli/energy.db --retain-days 90

# hand each reading to another program instead of a file
homewizard-cli export --format json --watch 2 \
  | curl -X POST "http://localhost:8086/write?db=energy" --data-binary @-
```

The default format is `influx`, line protocol, because the common case is a time-series database.
Anything the command prints goes to stdout unless `--file` redirects it.

| Option | What it does |
|---|---|
| `--watch` | Poll interval in seconds |
| `--format` | `influx`, `json`, `csv`, `tsv`, `mqtt`, `prometheus`, `env`, `minimal`, `raw` |
| `--file` | Write to a file instead of stdout |
| `--rotate daily\|hourly` | Start a new file per period, renaming the previous one |
| `--broker`, `--topic`, `--qos` | MQTT target and quality of service |
| `--skip-unchanged` | Skip a write when nothing changed since the last poll |
| `--fields` | Narrow the schema-less formats to these fields |
| `--delta`, `--agg`, `--until` | As in chapters 10 and 11 |
| `--alert-webhook`, `--alert-cmd`, `--alert-cooldown` | As in chapter 11 |
| `--metrics-port` | Prometheus endpoint on this port (0 disables it) |
| `--pid-file` | Write a PID file, removed on exit |
| `--db`, `--retain-days` | Log to SQLite and prune rows older than N days |

What it does when things go wrong:

- **Backoff.** A failed fetch or write retries with exponential backoff: 1 second, doubling to a
  60-second ceiling, reset after the next success.
- **Rotation is safe.** A rename that fails is retried, and if the new file cannot be opened the
  previous one is put back under its current name, so a record is never filed under the wrong
  period.
- **A running process is not doubled.** An existing, live PID in the PID file stops the command
  with exit code 1; a stale PID is ignored and overwritten.
- **Ctrl+C and SIGTERM shut down cleanly:** MQTT connections close, files flush, the metrics
  server stops, the PID file is removed.

## 19. Serve a REST proxy

`serve` puts a FastAPI app in front of the meter, for a dashboard or a script that cannot hold a
token itself. It needs `fastapi` and `uvicorn` (`pip install "homewizard-cli[dev]"`).

```bash
homewizard-cli serve
```

```
Proxy auth token (generated): 5Vb1...
  Callers must send: Authorization: Bearer <proxy token>
P1 Meter at 192.168.1.100 — OK
Starting proxy at http://127.0.0.1:8000
Proxying to P1 Meter at 192.168.1.100
```

The proxy holds the meter's token, so it authenticates its own callers instead of handing out
readings to anyone who can reach the port. Every route needs the proxy token — including `/` and
`/obis/{code}` — and a request without it gets a `401` without the meter being contacted. The token
is generated per run and printed once; pass `--auth-token` to reuse a stable one. A proxy started
without a token refuses every caller rather than running open.

```bash
homewizard-cli serve --port 9000 --cache 10 --auth-token "$PROXY_TOKEN"
```

```bash
curl -H "Authorization: Bearer $PROXY_TOKEN" http://localhost:8000/api/measurement  # v2
curl -H "Authorization: Bearer $PROXY_TOKEN" http://localhost:8000/api/v1/data      # v1
curl -H "Authorization: Bearer $PROXY_TOKEN" http://localhost:8000/obis/1-0:1.8.1
```

| Option | What it does |
|---|---|
| `--bind` | Address to listen on (default `127.0.0.1`; `0.0.0.0` exposes it to the LAN) |
| `--port` | Port (default `8000`) |
| `--cache` | Cache proxied responses for N seconds (default 0, off) |
| `--auth-token` | Token callers must send; generated and printed when omitted |

The proxy checks that it can reach the meter before it starts, and refuses to start if it cannot.

## 20. Feed Home Assistant

`hass` writes the configuration Home Assistant needs, for MQTT or for REST sensors.

```bash
homewizard-cli hass --mqtt
```

```json
{"topic": "homeassistant/sensor/ABC123/power/config", "payload": {"name": "P1 Meter Power", "state_topic": "homewizard/ABC123/state", "unit_of_measurement": "W", "device_class": "power", "state_class": "measurement", "unique_id": "ABC123_power", "device": {"identifiers": ["ABC123"], "name": "P1 Meter", "model": "HWE-P1", "manufacturer": "HomeWizard"}}}
```

```bash
homewizard-cli hass --rest
```

```json
{"sensor": [{"platform": "rest", "name": "Power", "device_class": "power", "value_template": "{{ value_json.active_power_w }}", "resource": "https://192.168.1.100/api/measurement", "device": {"identifiers": ["ABC123"], "name": "P1 Meter", "manufacturer": "HomeWizard"}}]}
```

Seven sensors: Power, Energy Import, Energy Export, Gas, Water, Voltage L1, Current L1. MQTT is the
default when you name neither mode.

On API v2 the REST sensors read the token-protected measurement endpoint themselves, so they need
the credential too. Pass `--token` (or set `token` in the config file) and every sensor carries
`headers: {Authorization: Bearer <token>}`. Without a token the command still prints the sensors,
with a warning, because they will answer 401 until you add the header yourself.

```bash
homewizard-cli hass --rest --token "$HW_TOKEN"
```

The command prints one JSON object; paste its `sensor:` list into Home Assistant's
`configuration.yaml`. The MQTT variant pairs with `export --format mqtt`, which publishes the state
topic these sensors read.

| Option | What it does |
|---|---|
| `--mqtt` | Print one discovery topic/payload per sensor |
| `--rest` | Print one configuration block with all sensors |
| `--topic-prefix` | MQTT state topic prefix (default `homewizard`) |

## 21. Manage the device

These change the device. Four of them exist only on API v2 and need a token.

### Tokens: `pair`, `users`

```bash
homewizard-cli pair                     # press the device button within 30 seconds
homewizard-cli pair --name local/myapp
```

```
User:  local/cli
Token: abc123def456...
```

```bash
homewizard-cli users list   --token <token>
homewizard-cli users delete --name local/admin --token <token>
```

```
Deleted: {"status": "ok"}
```

### Settings: `system`

```bash
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
homewizard-cli system --cloud false
homewizard-cli system --cloud-toggle
homewizard-cli system --led-brightness 50
homewizard-cli system --api-version v1 --cloud false    # v1 can only toggle the cloud
```

| Option | What it does |
|---|---|
| `--cloud true\|false` | Set the cloud connection |
| `--cloud-toggle` | Flip the current value |
| `--led-brightness N` | Status LED brightness, 0–100 (v2) |

### Battery: `batteries`

```bash
homewizard-cli batteries --token <token>
homewizard-cli batteries --mode to_full --token <token>
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

Modes: `zero`, `to_full`, `standby`, `predictive`.

### Energy Socket: `state`

```bash
homewizard-cli state
homewizard-cli state --power-on
homewizard-cli state --power-off
homewizard-cli state --brightness 50
homewizard-cli state --switch-lock
homewizard-cli state --switch-unlock
```

| Option | What it does |
|---|---|
| `--power-on`, `--power-off` | Switch the socket |
| `--switch-lock`, `--switch-unlock` | Prevent or allow the physical button |
| `--brightness N` | LED brightness, 0–100 |

### A light you can see: `identify`, `reboot`

```bash
homewizard-cli identify --count 3
```

```
LED blink triggered on P1 Meter (3x)
```

```bash
homewizard-cli reboot --token <token>
```

```
Reboot result: {"status": "ok"}
```

`reboot` takes the device off the network for a moment; everything that polls it will error until
it is back.

## 22. Watch it on a dashboard

A full-screen TUI with live panels and a sparkline, refreshed every 2 seconds by default.

```bash
homewizard-cli dashboard
homewizard-cli dashboard --watch 5
```

```
┌────────────────────────────────────────────────────────┐
│ P1 Meter: SDM230  |  WiFi: MyNetwork (78%)            │
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

`--watch` is the refresh interval, and it defaults to 2 seconds, unlike every other command. Add
`--db` to log each refresh to the history file. The dashboard watches one device; there is no
multi-device mode.

## 23. Fetch everything at once

`combined` asks for device info, the measurement, system settings, state and batteries in one
round of parallel requests, and prints the set.

```bash
homewizard-cli combined
homewizard-cli combined --host 192.168.1.100
```

That is four or five requests in the time of one, which matters when a slow meter is the reason a
script is slow. `--db` logs the measurement like any other read.

# Part V: Reference

## 24. Global options

These work before or after a subcommand. Before it, they apply to the bare command and a note
tells you if a subcommand ignored them; after it, they apply to that command.

| Option | Short | Default | What it does |
|---|---|---|---|
| `--host` | `-H` | discovered or configured | Meter address |
| `--timeout` | `-t` | `3.0`, or the config value | HTTP timeout in seconds |
| `--proxy` | | none | HTTP proxy, `scheme://host:port` |
| `--format` | `-f` | `auto` | Output format (chapter 8) |
| `--api-version` | | `v2` | `v1` or `v2`; anything else is refused |
| `--token` | | none | API v2 Bearer token |
| `--no-verify` | | off | Skip TLS verification (v2) |
| `--no-color` | | off | No ANSI colours |
| `--quiet` | `-q` | off | Errors only |
| `--verbose` | `-v` | off | Show HTTP request details |
| `--version` | | | Print the version and exit |
| `--install-completion`, `--show-completion` | | | Shell completion for bash, zsh, fish, PowerShell |

The host is resolved as: `--host`, then `[default] host` in the config file, then the cached
discovery result. With none of them the command stops with `DeviceNotFoundError` (exit 2) rather
than trying an empty address.

## 25. Command reference

| Command | One line |
|---|---|
| `homewizard-cli` | The main live fields as a table |
| `data` | The full reading, filterable |
| `power` | Live power, optionally with trend |
| `energy` | Cumulative import and export |
| `gas` | Gas total |
| `water` | Water total and flow |
| `quality` | Sag, swell and outage counters |
| `telegram` | The raw DSMR telegram |
| `info` | Device identity, firmware, Wi-Fi |
| `system` | Read or change system settings |
| `identify` | Blink the LED |
| `reboot` | Restart the device (v2) |
| `pair` | Create an API token (v2) |
| `users` | List or delete API tokens (v2) |
| `batteries` | Read or set battery mode (v2) |
| `state` | Energy Socket power, lock, brightness |
| `ping` | ICMP reachability |
| `discover` | Find devices over mDNS |
| `dashboard` | Full-screen live view |
| `export` | Continuous writes to a file, MQTT or stdout |
| `serve` | REST proxy in front of the meter |
| `combined` | Every model in one round of requests |
| `hass` | Home Assistant configuration |
| `cost` | Price a reading or a period |
| `history` | Query the SQLite archive |
| `config` | Validate or show the config file |

Flags are listed per command in Part IV; the tables in chapters 13–23 are the reference.

## 26. Exit codes

A script can branch on the exit code instead of parsing the message.

| Code | Error | Meaning |
|---|---|---|
| 1 | `P1Error` | Something unspecified went wrong |
| 2 | `DeviceNotFoundError`, `InvalidOptionError` | No reachable meter, or a value this build refuses |
| 3 | `HttpError` | The meter answered with a non-2xx status |
| 4 | `TimeoutError` | The request timed out; the message names the request |
| 5 | `ParseError` | The response could not be parsed |
| 6 | `CrcMismatchError` | The telegram checksum did not match |
| 7 | `WriteError` | A file or MQTT write failed |
| 8 | `UnsupportedError` | The device does not support this feature |
| 10 | `UntilConditionMetError` | An `--until` condition was met |

Messages name the thing that failed rather than the layer:

```
Timeout after 3.0s: GET http://192.168.1.100/api/v1/data
```

A failure to connect is a `DeviceNotFoundError` naming the host, a timeout or an HTTP error names
the request, and a body that cannot be parsed says so. Errors print in red and set the code above.

Device capability detection is not implemented: commands do not check the device type first, so
asking a P1 Meter for battery state surfaces the meter's own HTTP error.

## 27. Files and environment

| Path | What it holds |
|---|---|
| `~/.config/homewizard-cli/config.toml` | Your defaults (chapter 12) |
| `~/.config/homewizard-cli/host` | The cached discovery result, valid 24 hours |
| `~/.config/homewizard-cli/energy.db` | The default history file |
| `~/.config/homewizard-cli/homewizard-ca.pem` | A CA certificate for v2, if you install one |

| Variable | Effect |
|---|---|
| `HW_DB` | Default path for `history` and `--db` |
| `NO_PROXY` / `no_proxy` | Hosts that skip the proxy (exact match, no wildcards) |
| `HTTP_PROXY`, `HTTPS_PROXY` and their lowercase forms | Proxy to use when none is given |
| `HW_CONDITION`, `HW_DATA` | Set for `--alert-cmd` (chapter 11) |
| `NO_COLOR` | Set by `--no-color` for the duration of the run |

# Part VI: Operations

## 28. Run it unattended

`export` is the command to leave running. A systemd unit that logs, rotates, prunes and exposes
metrics:

```ini
[Unit]
Description=HomeWizard P1 Meter data export
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=homewizard
ExecStart=homewizard-cli export --watch 10 --format influx --file /var/log/homewizard/readings.log --rotate daily --metrics-port 9090 --pid-file /run/homewizard-export.pid --skip-unchanged --db /var/lib/homewizard/energy.db --retain-days 365
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
journalctl -u homewizard-export -f
```

Two things make this safe to restart: the PID file refuses to run two exporters over one file, and
SIGTERM flushes what is open before exit. `Restart=on-failure` covers the case where the meter is
power-cycled.

## 29. Scrape the metrics endpoint

`export --metrics-port N` starts a small HTTP server with `GET /metrics` in Prometheus format:

| Metric | Meaning |
|---|---|
| `homewizard_readings_total` | Successful readings |
| `homewizard_errors_total` | Failed reads or writes |
| `homewizard_last_poll_timestamp_seconds` | Unix time of the last successful poll |

```yaml
scrape_configs:
  - job_name: 'homewizard'
    static_configs:
      - targets: ['localhost:9090']
```

That block goes in your Prometheus configuration, `prometheus.yml` by default.

The endpoint is off unless you name a port. Bind it to localhost or a private interface; it has no
authentication of its own.

## 30. Stream over a WebSocket

Instead of asking the meter every N seconds, you can let it push. `data --ws` subscribes to
`wss://<host>/api/ws`, which only exists on API v2.

```bash
pip install "homewizard-cli[ws]"
homewizard-cli data --ws                 # one message, then exit
homewizard-cli data --ws --watch 10      # idle timeout: close after 10 seconds of silence
homewizard-cli data --ws --until "active_power_w > 5000"
```

Without `--watch` you get a single message and the connection closes. With `--watch N`, N becomes
the wait for each message: if nothing arrives within N seconds the client simply waits again. The
wait is 30 seconds when you do not pass `--watch`. The `websockets` package is imported only when
you ask for this, so the extra is optional; without it you get a message telling you which extra to
install. `--db` is not supported here, because messages are pushed rather than polled.

## 31. Route through a proxy

Resolution order:

1. `--proxy`.
2. `NO_PROXY` / `no_proxy`, matched exactly against the host; a match skips the proxy.
3. `HTTPS_PROXY` for v2, `HTTP_PROXY` for v1, in either case.

`/etc/hosts` entries are honoured as usual, and proxy environment variables are respected exactly
as `httpx` defines them.

## 32. Certificates on API v2

The meter serves a certificate signed by a private HomeWizard CA, which no system trust store
carries. The package ships no CA of its own, so a default v2 connection fails verification against
a real device. Pick one of these:

```bash
# 1. Install the CA you trust on the device, then verification works as usual
cp vendor-ca.pem ~/.config/homewizard-cli/homewizard-ca.pem

# 2. Skip verification, which requires a token
homewizard-cli data --no-verify --token MY_TOKEN
```

`--no-verify` without a token is refused with exit code 1: turning verification off while also
sending no credential is almost always a mistake. With a token it proceeds and logs that the
connection is unverified. A CA file at the path above is loaded when present; a malformed one is
ignored with a warning instead of crashing the client.

## 33. Keep the poll rate sane

Polling faster than once a second can make the meter unresponsive; the CLI prints a warning and
carries on:

```
Warning: Polling interval 0.5s is below recommended minimum (1.0s).
         Device may become unresponsive.
```

Prefer `--ws` for anything under a second: the meter pushes on its own schedule and you get every
value without asking. For writes into a database, `--skip-unchanged` removes duplicate rows when
the meter reports the same values.

# Part VII: The project

## 34. Status and limits

What is deliberately unfinished, so you know what you are relying on:

- **No device capability detection.** Commands do not check what kind of device they are talking
  to. Ask a P1 Meter for battery state and you get the device's HTTP error, not a friendly refusal.
- **v2-only commands.** `reboot`, `pair`, `users`, `batteries` and the write flags of `state` need
  API v2 and a token. v1 has no equivalent.
- **The dashboard is single-device.** There is no multi-device or `--all` mode.
- **Optional fields depend on the hardware.** Phase 2 and 3 fields, T3/T4 tariffs, gas and water
  only exist when the meter and its modules provide them.
- **v1 has no reading time.** `timestamp` stays empty on v1; CSV and TSV use the export clock.
- **Water needs a water module.** Without one, the `external` list has no water entry.
- **`--watch` needs an interval.** Only `dashboard` has a default.
- **`mqtt` is an `export` format.** Other commands refuse it and point here.
- **The package ships no CA.** See chapter 32.
- **The release workflow's PyPI step is a known leftover.** It fails on every tag by the owner's
  decision not to publish to PyPI; the release is the tag and the GitHub release page.

Bugs and gaps are tracked as GitHub issues, with the reproduction attached.

## 35. Development

```bash
git clone https://github.com/SwordfishTrumpet/homewizard-cli
cd homewizard-cli
uv sync
```

The checks, in the order they are worth running:

```bash
uv run ruff check homewizard_cli/ tests/                                  # lint
uv run python -m mypy --check-untyped-defs homewizard_cli/ tests/          # types
uv run python -m pytest tests/ -v                                        # tests
uv run python -m pytest tests/test_commands.py -v                        # one file
uv run python -m pytest tests/ --cov=homewizard_cli --cov-report=term-missing
uv run python -m sphinx -b html docs docs/_build/html                    # API docs
uv run pre-commit install                                                # the same checks on commit
uv run pre-commit run --all-files
```

They are also exposed as `package.json` scripts, so a tool that asks the repository what to run
gets an answer. Python is the implementation language; the manifest carries only these commands,
and `package-lock.json` marks npm as the tool that runs them.

```bash
npm run lint        # ruff
npm run typecheck   # mypy --check-untyped-defs
npm run test        # pytest
npm run test:fast   # pytest, stopping at the first failure
npm run build       # uv build, the wheel and sdist
```

What it is built from:

| Component | Library | Purpose |
|---|---|---|
| CLI | [Typer](https://typer.tiangolo.com/) 0.27.1+ | Routing, completions |
| HTTP | [httpx](https://www.python-httpx.org/) 0.28.1+ | Async requests |
| Models | [Pydantic](https://docs.pydantic.dev/) 2.13.4+ | Validation, v1↔v2 mapping |
| Output | [Rich](https://rich.readthedocs.io/) 15.0.0+ | Tables, panels, sparklines |
| Discovery | [python-zeroconf](https://github.com/python-zeroconf/python-zeroconf) 0.150.0+ | mDNS |
| Config | `tomllib` (stdlib) | TOML |
| WebSocket (optional) | [websockets](https://websockets.readthedocs.io/) 17.0.1+ | `data --ws` |
| Proxy (optional) | [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) | `serve` |
| MQTT (optional) | [paho-mqtt](https://www.eclipse.org/paho/) 2.1+ | `export --format mqtt` |

Fixtures live in `tests/fixtures/` (for example `api.json`, `data.json` and `system.json`). The
mock patterns follow the client a command uses: patch `resolve_client` for v1 and v2 commands
(returning `Measurement` from `get_json_v2`), and patch `P1ClientV2` directly for the v2-only
commands.

Releases are tags on `main`, and their notes are generated from the commits since the previous
tag.

## 36. License

MIT. See the [GitHub repository](https://github.com/SwordfishTrumpet/homewizard-cli) for the
license text.
