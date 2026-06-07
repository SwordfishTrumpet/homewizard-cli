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
class TariffConfig:
    """[tariffs] section configuration."""

    t1_rate: float = 0.30
    t2_rate: float = 0.20
    t3_rate: float = 0.25
    t4_rate: float = 0.15
    export_credit: float = 0.10
    currency: str = "EUR"


@dataclass
class Config:
    """Parsed configuration."""

    host: str | None = None
    timeout: float | None = None
    format: str | None = None
    timestamp_format: str | None = None
    token: str | None = None
    no_verify: bool | None = None
    export: ExportConfig | None = None
    tariffs: TariffConfig | None = None


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


def _load_tariff_config(data: dict) -> TariffConfig | None:
    """Load [tariffs] section from parsed TOML data."""
    tariff_data = data.get("tariffs", {})
    if not tariff_data:
        return None
    return TariffConfig(
        t1_rate=tariff_data.get("t1_rate", 0.30),
        t2_rate=tariff_data.get("t2_rate", 0.20),
        t3_rate=tariff_data.get("t3_rate", 0.25),
        t4_rate=tariff_data.get("t4_rate", 0.15),
        export_credit=tariff_data.get("export_credit", 0.10),
        currency=tariff_data.get("currency", "EUR"),
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
            token=default.get("token"),
            no_verify=default.get("no_verify"),
            export=_load_export_config(data),
            tariffs=_load_tariff_config(data),
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
    if "token" in default and not isinstance(default["token"], str):
        issues.append("default.token must be a string")
    if "no_verify" in default and not isinstance(default["no_verify"], bool):
        issues.append("default.no_verify must be a boolean")

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


def resolve_token(token: str | None) -> str | None:
    """Return token from CLI arg or config file."""
    if token is not None:
        return token
    cfg = load_config()
    return cfg.token


def resolve_no_verify(no_verify: bool) -> bool:
    """Return whether to skip SSL verification from CLI arg or config.
    
    If the CLI arg is False (default), falls back to config file.
    If the CLI arg is True, respects the explicit choice.
    """
    if no_verify:
        return True
    cfg = load_config()
    return bool(cfg.no_verify)
