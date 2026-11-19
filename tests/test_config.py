from unittest.mock import patch

import pytest

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
    """No host anywhere raises DeviceNotFoundError instead of a cryptic
    socket error at connect time (LOW-12)."""
    from homewizard_cli.errors import DeviceNotFoundError

    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(DeviceNotFoundError):
            resolve_host(None)


def test_resolve_host_no_host_raises_guidance():
    """LOW-12: empty host must raise DeviceNotFoundError with actionable guidance."""
    from homewizard_cli.errors import DeviceNotFoundError

    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(DeviceNotFoundError) as exc_info:
            resolve_host(None)
    assert "--host" in str(exc_info.value)
    assert exc_info.value.code == 2


# ── typed config values (issues #36, #44) ─────────────────────


def test_quoted_no_verify_is_ignored_not_true():
    """#36: no_verify = "false" must not disable TLS verification."""
    toml_content = """
[default]
host = "192.168.1.1"
no_verify = "false"
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        config = load_config()
        assert config.no_verify is None


def test_boolean_no_verify_is_kept():
    toml_content = """
[default]
no_verify = true
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        assert load_config().no_verify is True


def test_wrong_typed_values_are_ignored():
    """A string timeout, qos or metrics_port is dropped instead of reaching httpx."""
    toml_content = """
[default]
host = "192.168.1.1"
timeout = "5"
[export]
qos = "2"
metrics_port = "9090"
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        config = load_config()
    assert config.host == "192.168.1.1"
    assert config.timeout is None
    assert config.export is not None
    assert config.export.qos is None
    assert config.export.metrics_port is None


def test_invalid_format_falls_back_to_default():
    toml_content = """
[default]
format = "yamlish"
"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        assert load_config().format is None


def test_unparsable_config_records_the_parse_error():
    """#44: a TOML typo must not be swallowed into defaults."""
    toml_content = '[default]\nhost = "192.0.2.10"\ntimeout = 1.5 "oops"\n'
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        config = load_config()
    assert config.parse_error is not None
    assert "Invalid TOML" in config.parse_error


def test_resolve_host_reports_the_parse_error():
    """#44: the recovery must name the parse failure, not repeat 'set host'."""
    from homewizard_cli.errors import DeviceNotFoundError

    toml_content = '[default]\nhost = "192.0.2.10"\ntimeout = 1.5 "oops"\n'
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=toml_content),
    ):
        with pytest.raises(DeviceNotFoundError) as exc_info:
            resolve_host(None)
    assert "Invalid TOML" in str(exc_info.value)


# ── #29: a subcommand must honour [default] timeout and format ──


def test_resolve_timeout_prefers_the_cli_value():
    from homewizard_cli.config import resolve_timeout

    assert resolve_timeout(1.5) == 1.5


def test_resolve_timeout_reads_the_config_file():
    """#29: a command passing None must pick up [default] timeout."""
    from homewizard_cli.config import resolve_timeout

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value='[default]\ntimeout = 10.0\n'),
    ):
        assert resolve_timeout(None) == 10.0


def test_resolve_timeout_falls_back_to_the_constant():
    from homewizard_cli.config import resolve_timeout

    with patch("pathlib.Path.exists", return_value=False):
        assert resolve_timeout(None) == DEFAULT_TIMEOUT


def test_resolve_format_reads_the_config_file():
    """#29: [default] format was resolved and then discarded for subcommands."""
    from homewizard_cli.config import resolve_format

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value='[default]\nformat = "csv"\n'),
    ):
        assert resolve_format(None) == "csv"


def test_resolve_format_prefers_the_cli_value():
    from homewizard_cli.config import resolve_format

    assert resolve_format("json") == "json"
