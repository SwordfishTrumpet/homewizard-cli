# CHANGELOG

All notable changes to homewizard-cli will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-05-29

### Added
- API v2 support with HTTPS, Bearer token auth, and SSL certificate handling
- v2-only commands: `reboot`, `pair`, `users list`, `users delete`, `batteries`
- `--api-version` flag on all commands (default: `v2`)
- `--token` and `--no-verify` options for v2 authentication
- WebSocket support via `data --ws` flag (v2 only, optional `websockets` dep)
- `hass` command for Home Assistant MQTT discovery and REST configuration generation
- `dashboard` command with Rich Live/Layout for real-time TUI display
- `serve` command with FastAPI + uvicorn REST proxy
- `water` command for water meter readings (flow and total consumption)
- `combined` command for parallel multi-endpoint data fetching
- `config` command with `--validate` and `--show` flags
- Multi-device dashboard via `dashboard --all` and `dashboard --hosts`
- Device capability detection with `UnsupportedError` (exit code 8)
- Rolling aggregates (`--agg` flag) with mean/min/max/stddev via `Aggregator` class
- Alert actions: `--alert-webhook`, `--alert-cmd`, `--alert-cooldown`
- Composite expression conditions: `AND`/`OR`/`NOT` boolean operators in `--until`
- Prometheus metrics endpoint (`--metrics-port`) in export command
- PID file support (`--pid-file`) for process management
- File rotation (`--rotate daily|hourly`) in export command
- Go-style template output (`--template`) with `{{.field}}W` syntax
- Delta tracking (`--delta`) with colored green/red rich output
- 3-phase L2/L3 sag/swell counters in `quality` command
- T3/T4 tariff display in `energy --tariffs`
- Export format support: InfluxDB line protocol, Prometheus exposition, MQTT, env
- OBIS service endpoint (`GET /obis/{code}`) in serve command
- JSONPath query support with `--query "$.field_name"`
- Bundled SSL CA certificate for HomeWizard devices
- Hostname verification for v2 client
- Telegram parser robustness for non-ASCII characters
- Pre-commit hooks: ruff, mypy, pytest, codespell, bandit
- Sphinx API documentation with furo theme

### Changed
- Empty `homewizard-cli` (no subcommand) now runs `_default_async` properly
- CLI architecture: all commands top-level, no v1/v2 prefix
- `Measurement` model unifies v1/v2 data using field name mapping
- `DataResponse` is now a backward-compat alias for `Measurement`
- Client factory (`resolve_client`) handles both v1 and v2 polymorphically
- Discovery prefers v2 mDNS (`_homewizard._tcp.local.`) first, falls back to v1
- error `__str__` no longer includes "Error:" prefix
- `system` command supports v2 settings (6 fields vs v1's single `cloud_enabled`)
- `info` command shows different fields based on API version and available data
- `export` option resolution: CLI > config > hardcoded default via `_resolve_export_option()`

### Fixed
- `serve` command now uses correct protocol (https for v2) and passes auth headers
- `pair` command error handling uses `isinstance(e, HttpError) and e.status == 403`
- `energy --tariffs` now displays T3/T4 lines conditionally
- `quality` command now displays L2/L3 sag/swell counts conditionally
- v2 timestamp conversion from ISO 8601 to compact `YYMMDDhhmmss` ints
- v2 `external` device list now properly converted
- All 15 mypy errors resolved (`--check-untyped-defs` clean across 84 source files)
- `TRD.md` stale sections updated to match current state

### Removed
- `--cache` global option (dead code)
- `convert_v2_measurement()` utility function

## [0.1.0] — Initial Release

### Added
- CLI framework with Typer
- v1 API support via HTTP (port 80)
- Commands: `data`, `power`, `energy`, `gas`, `quality`, `telegram`, `info`, `identify`, `ping`, `discover`, `export`, `system`
- Output formats: table (Rich), JSON, CSV, TSV, InfluxDB, Prometheus, minimal, raw
- mDNS discovery via `_hwenergy._tcp.local.`
- Watch mode with configurable polling intervals
- Expression conditions (`--until`) for automated exit
- Configuration file at `~/.config/homewizard-cli/config.toml`
- Shell completions for bash, zsh, fish, PowerShell
