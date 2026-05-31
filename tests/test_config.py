from unittest.mock import patch

from homewizard_cli.config import (
    DEFAULT_FORMAT,
    DEFAULT_HOST,
    DEFAULT_TIMEOUT,
    Config,
    _load_export_config,
    load_config,
    resolve_host,
    validate_config,
)


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
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
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
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        config = load_config()
        assert config.host == "192.168.1.1"
        assert config.timeout is None


def test_config_invalid_toml():
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="invalid toml {{"),
    ):
        config = load_config()
        assert config.host is None


def test_config_defaults_constants():
    assert DEFAULT_HOST == ""
    assert DEFAULT_TIMEOUT == 3.0
    assert DEFAULT_FORMAT == "auto"


def test_validate_config_no_file():
    with patch("pathlib.Path.exists", return_value=False):
        result = validate_config()
        assert "not found" in result[0]


def test_validate_config_invalid_toml():
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="[[["),
    ):
        result = validate_config()
        assert any("Invalid" in r for r in result)


def test_validate_config_valid():
    toml_content = """
[default]
host = "192.168.1.1"
timeout = 5.0
format = "json"
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert "valid" in result[0]


def test_export_format_validation():
    toml_content = """
[export]
format = 123
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("export.format must be a string" in r for r in result)


def test_export_watch_validation():
    toml_content = """
[export]
watch = "invalid"
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("export.watch must be a number" in r for r in result)


def test_export_qos_validation():
    toml_content = """
[export]
qos = 1.5
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("export.qos must be an integer" in r for r in result)


def test_export_metrics_port_validation():
    toml_content = """
[export]
metrics_port = "invalid"
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("export.metrics_port must be an integer" in r for r in result)


def test_load_export_config_empty():
    assert _load_export_config({}) is None


def test_validate_config_host_not_string():
    toml_content = """
[default]
host = 123
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("default.host must be a string" in r for r in result)


def test_validate_config_timeout_below_threshold():
    toml_content = """
[default]
timeout = 0.05
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("default.timeout must be >= 0.1" in r for r in result)


def test_validate_config_unknown_format():
    toml_content = """
[default]
format = "foo"
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("not a valid format" in r for r in result)


def test_validate_config_invalid_timestamp_format():
    toml_content = """
[default]
timestamp_format = 123
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("default.timestamp_format must be a string" in r for r in result)


def test_validate_config_valid_export():
    toml_content = """
[export]
format = "json"
watch = 5.0
qos = 1
metrics_port = 9090
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        result = validate_config()
        assert any("Config file is valid" in r for r in result)


def test_resolve_host_explicit():
    assert resolve_host("1.2.3.4") == "1.2.3.4"


def test_resolve_host_no_host_no_config():
    with patch("pathlib.Path.exists", return_value=False):
        assert resolve_host(None) == ""
