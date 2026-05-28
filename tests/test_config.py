import pytest
from pathlib import Path
from unittest.mock import patch
from homewizard_cli.config import load_config, Config


def test_config_defaults():
    config = Config()
    assert config.host is None
    assert config.timeout is None
    assert config.format is None


def test_config_from_toml():
    toml_content = """
[default]
host = "192.168.1.1"
timeout = 5.0
format = "json"
"""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value=toml_content):
            config = load_config()
            assert config.host == "192.168.1.1"
            assert config.timeout == 5.0
            assert config.format == "json"


def test_config_no_file():
    with patch("pathlib.Path.exists", return_value=False):
        config = load_config()
        assert config.host is None
        assert config.timeout is None


def test_config_partial():
    toml_content = """
[default]
host = "192.168.1.1"
"""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value=toml_content):
            config = load_config()
            assert config.host == "192.168.1.1"
            assert config.timeout is None


def test_config_invalid_toml():
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value="invalid toml {{"):
            config = load_config()
            assert config.host is None
