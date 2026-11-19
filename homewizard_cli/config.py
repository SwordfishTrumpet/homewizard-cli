"""Config file handling for homewizard-cli."""

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

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
    #: Set when config.toml exists but could not be parsed, so a command that
    #: needed the file can report the typo instead of "no host configured".
    parse_error: str | None = None


def _string(
    section: dict,
    key: str,
    section_name: str,
    choices: set[str] | None = None,
) -> str | None:
    """Read a string entry, ignoring (and reporting) a value of another type."""
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        log.warning(
            "config.toml: [%s] %s must be a string; ignoring %r",
            section_name,
            key,
            value,
        )
        return None
    if choices is not None and value not in choices:
        log.warning(
            "config.toml: [%s] %s is not one of %s; ignoring %r",
            section_name,
            key,
            ", ".join(sorted(choices)),
            value,
        )
        return None
    return value


def _number(
    section: dict,
    key: str,
    section_name: str,
    default: float | None = None,
) -> float | None:
    """Read a numeric entry, ignoring (and reporting) a value of another type."""
    value = section.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        log.warning(
            "config.toml: [%s] %s must be a number; ignoring %r",
            section_name,
            key,
            value,
        )
        return default
    return float(value)


def _integer(section: dict, key: str, section_name: str) -> int | None:
    value = section.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        log.warning(
            "config.toml: [%s] %s must be a whole number; ignoring %r",
            section_name,
            key,
            value,
        )
        return None
    return value


def _rate(section: dict, key: str, section_name: str, default: float) -> float:
    """Read a tariff rate, falling back to *default* when absent or unusable."""
    value = _number(section, key, section_name)
    return default if value is None else value


def _boolean(section: dict, key: str, section_name: str) -> bool | None:
    """Read a boolean entry, ignoring (and reporting) a value of another type.

    A quoted "false" is not false: read as a string it is truthy, and a truthy
    no_verify would switch TLS verification off on the value meant to keep it on
    (issue #36). Only a real TOML boolean counts.
    """
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        log.warning(
            "config.toml: [%s] %s must be true or false (unquoted); ignoring %r",
            section_name,
            key,
            value,
        )
        return None
    return value


def _load_export_config(data: dict) -> ExportConfig | None:
    """Load [export] section from parsed TOML data."""
    export_data = data.get("export", {})
    if not export_data:
        return None
    return ExportConfig(
        format=_string(export_data, "format", "export"),
        watch=_number(export_data, "watch", "export"),
        file=_string(export_data, "file", "export"),
        rotate=_string(export_data, "rotate", "export"),
        broker=_string(export_data, "broker", "export"),
        topic=_string(export_data, "topic", "export"),
        qos=_integer(export_data, "qos", "export"),
        skip_unchanged=_boolean(export_data, "skip_unchanged", "export"),
        fields=_string(export_data, "fields", "export"),
        delta=_boolean(export_data, "delta", "export"),
        metrics_port=_integer(export_data, "metrics_port", "export"),
        pid_file=_string(export_data, "pid_file", "export"),
    )


def _load_tariff_config(data: dict) -> TariffConfig | None:
    """Load [tariffs] section from parsed TOML data."""
    tariff_data = data.get("tariffs", {})
    if not tariff_data:
        return None
    return TariffConfig(
        t1_rate=_rate(tariff_data, "t1_rate", "tariffs", 0.30),
        t2_rate=_rate(tariff_data, "t2_rate", "tariffs", 0.20),
        t3_rate=_rate(tariff_data, "t3_rate", "tariffs", 0.25),
        t4_rate=_rate(tariff_data, "t4_rate", "tariffs", 0.15),
        export_credit=_rate(tariff_data, "export_credit", "tariffs", 0.10),
        currency=_string(tariff_data, "currency", "tariffs") or "EUR",
    )


def load_config() -> Config:
    """Load config from ~/.config/homewizard-cli/config.toml."""
    if not CONFIG_FILE.exists():
        return Config()

    try:
        data = tomllib.loads(CONFIG_FILE.read_text())
    except FileNotFoundError:
        return Config()
    except tomllib.TOMLDecodeError as e:
        # Swallowing the decode error discarded every configured default and
        # sent the user back to edit the file that just failed to parse (#44).
        return Config(parse_error=f"Invalid TOML in {CONFIG_FILE}: {e}")

    default = data.get("default", {})
    return Config(
        host=_string(default, "host", "default"),
        timeout=_number(default, "timeout", "default"),
        format=_string(default, "format", "default", VALID_FORMATS),
        timestamp_format=_string(default, "timestamp_format", "default"),
        token=_string(default, "token", "default"),
        no_verify=_boolean(default, "no_verify", "default"),
        export=_load_export_config(data),
        tariffs=_load_tariff_config(data),
    )


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
    """Return host from CLI arg, config file, or default.

    Raises DeviceNotFoundError (exit code 2) when no host is configured
    anywhere, instead of letting the client fail with a cryptic socket
    error at connect time (LOW-12).
    """
    if host is not None:
        return host
    cfg = load_config()
    resolved = cfg.host or DEFAULT_HOST
    if not resolved:
        from .errors import DeviceNotFoundError

        if cfg.parse_error:
            raise DeviceNotFoundError(
                f"Could not read {CONFIG_FILE}",
                f"{cfg.parse_error}. Fix that line, or pass --host <ip>.",
            )
        raise DeviceNotFoundError(
            "No P1 meter host configured",
            "Use --host <ip>, set 'host' in config.toml ([default] section), "
            "or run 'homewizard-cli discover'.",
        )
    return resolved


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
    return cfg.no_verify is True
