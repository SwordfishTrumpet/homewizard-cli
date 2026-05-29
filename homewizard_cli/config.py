"""Config file handling for homewizard-cli."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "homewizard-cli"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_HOST = ""
DEFAULT_TIMEOUT = 3.0
DEFAULT_FORMAT = "auto"
VALID_FORMATS = {
    "auto",
    "json",
    "table",
    "csv",
    "tsv",
    "influx",
    "prometheus",
    "env",
    "minimal",
    "raw",
}


@dataclass
class ExportConfig:
    """[export] section configuration."""

    format: str | None = None
    watch: float | None = None
    file: str | None = None
    rotate: str | None = None
    broker: str | None = None
    topic: str | None = None
    qos: int | None = None
    skip_unchanged: bool | None = None
    fields: str | None = None
    delta: bool | None = None
    metrics_port: int | None = None
    pid_file: str | None = None


@dataclass
class Config:
    """Parsed configuration."""

    host: str | None = None
    timeout: float | None = None
    format: str | None = None
    timestamp_format: str | None = None
    export: ExportConfig | None = None


def _load_export_config(data: dict) -> ExportConfig | None:
    """Load [export] section from parsed TOML data."""
    export_data = data.get("export", {})
    if not export_data:
        return None
    return ExportConfig(
        format=export_data.get("format"),
        watch=export_data.get("watch"),
        file=export_data.get("file"),
        rotate=export_data.get("rotate"),
        broker=export_data.get("broker"),
        topic=export_data.get("topic"),
        qos=export_data.get("qos"),
        skip_unchanged=export_data.get("skip_unchanged"),
        fields=export_data.get("fields"),
        delta=export_data.get("delta"),
        metrics_port=export_data.get("metrics_port"),
        pid_file=export_data.get("pid_file"),
    )


def load_config() -> Config:
    """Load config from ~/.config/homewizard-cli/config.toml."""
    if not CONFIG_FILE.exists():
        return Config()

    try:
        data = tomllib.loads(CONFIG_FILE.read_text())
        default = data.get("default", {})
        return Config(
            host=default.get("host"),
            timeout=default.get("timeout"),
            format=default.get("format"),
            timestamp_format=default.get("timestamp_format"),
            export=_load_export_config(data),
        )
    except (tomllib.TOMLDecodeError, FileNotFoundError):
        return Config()


def validate_config() -> list[str]:
    """Validate config file and return list of issues (empty = valid)."""
    issues = []
    if not CONFIG_FILE.exists():
        return ["Config file not found at " + str(CONFIG_FILE)]

    try:
        data = tomllib.loads(CONFIG_FILE.read_text())
    except Exception as e:
        return [f"Invalid TOML: {e}"]

    default = data.get("default", {})
    if "host" in default and not isinstance(default["host"], str):
        issues.append("default.host must be a string")
    if "timeout" in default:
        if not isinstance(default["timeout"], (int, float)):
            issues.append("default.timeout must be a number")
        elif default["timeout"] < 0.1:
            issues.append("default.timeout must be >= 0.1")
    if "format" in default and default["format"] not in VALID_FORMATS:
        issues.append(f"default.format '{default['format']}' is not a valid format")
    if "timestamp_format" in default and not isinstance(
        default["timestamp_format"], str
    ):
        issues.append("default.timestamp_format must be a string")

    export_data = data.get("export", {})
    if export_data:
        if "format" in export_data and not isinstance(export_data["format"], str):
            issues.append("export.format must be a string")
        if "watch" in export_data and not isinstance(
            export_data["watch"], (int, float)
        ):
            issues.append("export.watch must be a number")
        if "qos" in export_data and not isinstance(export_data["qos"], int):
            issues.append("export.qos must be an integer")
        if "metrics_port" in export_data and not isinstance(
            export_data["metrics_port"], int
        ):
            issues.append("export.metrics_port must be an integer")

    if not issues:
        issues.append("Config file is valid")

    return issues


def resolve_host(host: str | None) -> str:
    """Return host from CLI arg, config file, or default."""
    if host is not None:
        return host
    cfg = load_config()
    return cfg.host or DEFAULT_HOST
