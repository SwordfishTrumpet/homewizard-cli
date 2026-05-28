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
