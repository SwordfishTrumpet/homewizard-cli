"""Config file handling for homewizard-cli."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".config" / "homewizard-cli"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_HOST = "192.168.68.109"
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
class Config:
    """Parsed configuration."""

    host: Optional[str] = None
    timeout: Optional[float] = None
    format: Optional[str] = None


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

    if not issues:
        issues.append("Config file is valid")

    return issues
