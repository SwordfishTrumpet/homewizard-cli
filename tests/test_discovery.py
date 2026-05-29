import pytest
from unittest.mock import patch
from homewizard_cli.discovery import discover_host, _get_cache
from homewizard_cli.errors import DeviceNotFoundError


def test_get_cache_no_file():
    with patch("pathlib.Path.exists", return_value=False):
        assert _get_cache() is None


def test_get_cache_valid():
    import json
    from datetime import datetime

    cache_data = {
        "host": "192.168.1.100",
        "timestamp": datetime.now().isoformat(),
    }
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value=json.dumps(cache_data)):
            assert _get_cache() == "192.168.1.100"


@pytest.mark.asyncio
async def test_discover_explicit_host():
    host, from_cache = await discover_host(explicit_host="192.168.1.50")
    assert host == "192.168.1.50"
    assert from_cache is False


@pytest.mark.asyncio
async def test_discover_no_host_found():
    with patch("homewizard_cli.discovery._get_cache", return_value=None):
        with patch("homewizard_cli.discovery.discover_mdns_v2", return_value=None):
            with patch("homewizard_cli.discovery.discover_mdns", return_value=None):
                with patch("homewizard_cli.discovery.discover_arp", return_value=None):
                    with pytest.raises(DeviceNotFoundError):
                        await discover_host()
