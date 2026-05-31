from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from homewizard_cli.discovery import (
    _discover_all_mdns_for,
    _get_cache,
    _probe_host,
    _probe_host_info,
    _save_cache,
    discover_all_hosts,
    discover_arp,
    discover_host,
    discover_mdns,
    discover_mdns_v2,
)
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
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=json.dumps(cache_data)),
    ):
        assert _get_cache() == "192.168.1.100"


@pytest.mark.asyncio
async def test_discover_explicit_host():
    host, from_cache = await discover_host(explicit_host="192.168.1.50")
    assert host == "192.168.1.50"
    assert from_cache is False


@pytest.mark.asyncio
async def test_discover_no_host_found():
    with (
        patch("homewizard_cli.discovery._get_cache", return_value=None),
        patch("homewizard_cli.discovery.discover_mdns_v2", return_value=None),
        patch("homewizard_cli.discovery.discover_mdns", return_value=None),
        patch("homewizard_cli.discovery.discover_arp", return_value=None),
        pytest.raises(DeviceNotFoundError),
    ):
        await discover_host()


# ── mDNS discovery ────────────────────────────────────────────


def _make_browser_mock(mock_zc, infos):
    """Return a ServiceBrowser side_effect that populates the listener."""
    call_count = [0]

    def browser_init(zc, type_, listener):
        for info in infos:
            if info:
                call_count[0] += 1
                listener.add_service(
                    zc, type_, f"dev{call_count[0]}._homewizard._tcp.local."
                )
        return MagicMock()

    return browser_init


@pytest.mark.asyncio
async def test_discover_mdns_v2_returns_ip():
    """Test discover_mdns_v2 finds a v2 device via mocked zeroconf."""
    mock_info = MagicMock()
    mock_info.addresses = [[192, 168, 1, 10]]
    mock_info.properties = {b"id": b"abc123"}

    mock_zc = MagicMock()
    mock_zc.get_service_info.return_value = mock_info

    with (
        patch("homewizard_cli.discovery.Zeroconf", return_value=mock_zc),
        patch(
            "homewizard_cli.discovery.ServiceBrowser",
            side_effect=_make_browser_mock(mock_zc, [mock_info]),
        ),
    ):
        result = await discover_mdns_v2(timeout=0.01)
        assert result == "192.168.1.10"


@pytest.mark.asyncio
async def test_discover_mdns_v2_no_devices():
    """Test discover_mdns_v2 returns None when no devices found."""
    mock_zc = MagicMock()
    mock_zc.get_service_info.return_value = None

    with (
        patch("homewizard_cli.discovery.Zeroconf", return_value=mock_zc),
        patch(
            "homewizard_cli.discovery.ServiceBrowser",
            side_effect=_make_browser_mock(mock_zc, []),
        ),
    ):
        result = await discover_mdns_v2(timeout=0.01)
        assert result is None


@pytest.mark.asyncio
async def test_discover_mdns_returns_ip():
    """Test discover_mdns finds a v1 device via mocked zeroconf."""
    mock_info = MagicMock()
    mock_info.addresses = [[192, 168, 1, 20]]
    mock_info.properties = {}

    mock_zc = MagicMock()
    mock_zc.get_service_info.return_value = mock_info

    with (
        patch("homewizard_cli.discovery.Zeroconf", return_value=mock_zc),
        patch(
            "homewizard_cli.discovery.ServiceBrowser",
            side_effect=_make_browser_mock(mock_zc, [mock_info]),
        ),
    ):
        result = await discover_mdns(timeout=0.01)
        assert result == "192.168.1.20"


@pytest.mark.asyncio
async def test_discover_mdns_no_devices():
    """Test discover_mdns returns None when no devices found."""
    mock_zc = MagicMock()
    mock_zc.get_service_info.return_value = None

    with (
        patch("homewizard_cli.discovery.Zeroconf", return_value=mock_zc),
        patch(
            "homewizard_cli.discovery.ServiceBrowser",
            side_effect=_make_browser_mock(mock_zc, []),
        ),
    ):
        result = await discover_mdns(timeout=0.01)
        assert result is None


@pytest.mark.asyncio
async def test_discover_all_mdns_for_multiple_devices():
    """Test _discover_all_mdns_for returns multiple entries."""
    mock_info1 = MagicMock()
    mock_info1.addresses = [[192, 168, 1, 10]]
    mock_info1.properties = {b"id": b"dev1"}
    mock_info2 = MagicMock()
    mock_info2.addresses = [[192, 168, 1, 11]]
    mock_info2.properties = {b"id": b"dev2"}

    call_count = [0]

    def get_service_info(type_, name):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_info1
        return mock_info2

    mock_zc = MagicMock()
    mock_zc.get_service_info.side_effect = get_service_info

    with (
        patch("homewizard_cli.discovery.Zeroconf", return_value=mock_zc),
        patch(
            "homewizard_cli.discovery.ServiceBrowser",
            side_effect=_make_browser_mock(mock_zc, [mock_info1, mock_info2]),
        ),
    ):
        result = await _discover_all_mdns_for("_homewizard._tcp.local.", timeout=0.01)
        assert len(result) == 2
        assert result[0]["ip"] == "192.168.1.10"
        assert result[1]["ip"] == "192.168.1.11"


# ── ARP discovery ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_discover_arp_finds_homewizard_mac():
    """Test discover_arp finds a device with a HomeWizard MAC prefix."""
    arp_content = (
        "IP address       HW type     Flags       HW address            "
        "Mask     Device\n"
        "192.168.1.50     0x1         0x2         5c:62:8b:01:02:03     *        "
        "eth0\n"
        "192.168.1.51     0x1         0x2         aa:bb:cc:dd:ee:ff     *        "
        "eth0\n"
    )

    with (
        patch("builtins.open", mock_open(read_data=arp_content)),
        patch("homewizard_cli.discovery._probe_host", return_value=True),
    ):
        result = await discover_arp(timeout=0.01)
        assert result == "192.168.1.50"


@pytest.mark.asyncio
async def test_discover_arp_finds_alt_mac_prefix():
    """Test discover_arp finds a device with the alternate MAC prefix."""
    arp_content = (
        "IP address       HW type     Flags       HW address            "
        "Mask     Device\n"
        "192.168.1.60     0x1         0x2         3c:61:05:01:02:03     *        "
        "eth0\n"
    )

    with (
        patch("builtins.open", mock_open(read_data=arp_content)),
        patch("homewizard_cli.discovery._probe_host", return_value=True),
    ):
        result = await discover_arp(timeout=0.01)
        assert result == "192.168.1.60"


@pytest.mark.asyncio
async def test_discover_arp_no_homewizard_devices():
    """Test discover_arp returns None when no HomeWizard MACs are present."""
    arp_content = (
        "IP address       HW type     Flags       HW address            "
        "Mask     Device\n"
        "192.168.1.51     0x1         0x2         aa:bb:cc:dd:ee:ff     *        "
        "eth0\n"
    )

    with patch("builtins.open", mock_open(read_data=arp_content)):
        result = await discover_arp(timeout=0.01)
        assert result is None


@pytest.mark.asyncio
async def test_discover_arp_file_not_found():
    """Test discover_arp handles missing /proc/net/arp gracefully."""
    with patch("builtins.open", side_effect=FileNotFoundError()):
        result = await discover_arp(timeout=0.01)
        assert result is None


@pytest.mark.asyncio
async def test_discover_arp_permission_error():
    """Test discover_arp handles permission denied gracefully."""
    with patch("builtins.open", side_effect=PermissionError()):
        result = await discover_arp(timeout=0.01)
        assert result is None


@pytest.mark.asyncio
async def test_discover_arp_probe_host_fails():
    """Test discover_arp skips devices that fail the probe."""
    arp_content = (
        "IP address       HW type     Flags       HW address            "
        "Mask     Device\n"
        "192.168.1.50     0x1         0x2         5c:62:8b:01:02:03     *        "
        "eth0\n"
    )

    with (
        patch("builtins.open", mock_open(read_data=arp_content)),
        patch("homewizard_cli.discovery._probe_host", return_value=False),
    ):
        result = await discover_arp(timeout=0.01)
        assert result is None


# ── discover_all_hosts ────────────────────────────────────────


@pytest.mark.asyncio
async def test_discover_all_hosts_multiple_devices():
    """Test discover_all_hosts aggregates v1 and v2 devices."""
    with (
        patch(
            "homewizard_cli.discovery.discover_all_mdns",
            return_value=[
                {
                    "ip": "192.168.1.10",
                    "name": "dev1",
                    "properties": {},
                    "host": "192.168.1.10",
                }
            ],
        ),
        patch(
            "homewizard_cli.discovery.discover_all_mdns_v2",
            return_value=[
                {
                    "ip": "192.168.1.11",
                    "name": "dev2",
                    "properties": {},
                    "host": "192.168.1.11",
                }
            ],
        ),
        patch(
            "homewizard_cli.discovery._probe_host_info",
            side_effect=[
                {"product_type": "HWE-P1", "serial": "S1", "product_name": "P1"},
                {
                    "product_type": "HWE-SKT",
                    "serial": "S2",
                    "product_name": "Socket",
                },
            ],
        ),
    ):
        result = await discover_all_hosts(timeout=0.01)
        assert len(result) == 2
        assert result[0]["host"] == "192.168.1.10"
        assert result[0]["product_type"] == "HWE-P1"
        assert result[1]["host"] == "192.168.1.11"
        assert result[1]["product_type"] == "HWE-SKT"


@pytest.mark.asyncio
async def test_discover_all_hosts_deduplicates_by_ip():
    """Test discover_all_hosts deduplicates devices with the same IP."""
    with (
        patch(
            "homewizard_cli.discovery.discover_all_mdns",
            return_value=[
                {
                    "ip": "192.168.1.10",
                    "name": "dev1",
                    "properties": {},
                    "host": "192.168.1.10",
                }
            ],
        ),
        patch(
            "homewizard_cli.discovery.discover_all_mdns_v2",
            return_value=[
                {
                    "ip": "192.168.1.10",
                    "name": "dev2",
                    "properties": {},
                    "host": "192.168.1.10",
                }
            ],
        ),
        patch(
            "homewizard_cli.discovery._probe_host_info",
            return_value={
                "product_type": "HWE-P1",
                "serial": "S1",
                "product_name": "P1",
            },
        ),
    ):
        result = await discover_all_hosts(timeout=0.01)
        assert len(result) == 1
        assert result[0]["host"] == "192.168.1.10"


@pytest.mark.asyncio
async def test_discover_all_hosts_ignores_unresponsive():
    """Test discover_all_hosts skips devices that don't respond to HTTP probe."""
    with (
        patch(
            "homewizard_cli.discovery.discover_all_mdns",
            return_value=[
                {
                    "ip": "192.168.1.10",
                    "name": "dev1",
                    "properties": {},
                    "host": "192.168.1.10",
                }
            ],
        ),
        patch("homewizard_cli.discovery.discover_all_mdns_v2", return_value=[]),
        patch(
            "homewizard_cli.discovery._probe_host_info",
            return_value=None,
        ),
    ):
        result = await discover_all_hosts(timeout=0.01)
        assert len(result) == 0


@pytest.mark.asyncio
async def test_discover_all_hosts_https_fallback():
    """Test discover_all_hosts falls back to HTTPS when HTTP probe fails."""
    with (
        patch(
            "homewizard_cli.discovery.discover_all_mdns",
            return_value=[
                {
                    "ip": "192.168.1.10",
                    "name": "dev1",
                    "properties": {},
                    "host": "192.168.1.10",
                }
            ],
        ),
        patch("homewizard_cli.discovery.discover_all_mdns_v2", return_value=[]),
        patch(
            "homewizard_cli.discovery._probe_host_info",
            side_effect=[
                None,
                {"product_type": "HWE-P1", "serial": "S1", "product_name": "P1"},
            ],
        ),
    ):
        result = await discover_all_hosts(timeout=0.01)
        assert len(result) == 1
        assert result[0]["product_type"] == "HWE-P1"


# ── Cache operations ────────────────────────────────────────────


def test_save_cache_writes_correct_path():
    import json
    from datetime import datetime

    with (
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.write_text") as mock_write,
    ):
        _save_cache("192.168.1.100")
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        written = json.loads(mock_write.call_args[0][0])
        assert written["host"] == "192.168.1.100"
        assert "timestamp" in written
        datetime.fromisoformat(written["timestamp"])


def test_get_cache_malformed_json():
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="not valid json"),
    ):
        assert _get_cache() is None


def test_get_cache_missing_timestamp():
    import json

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=json.dumps({"host": "1.2.3.4"})),
    ):
        assert _get_cache() is None


def test_get_cache_expired():
    import json
    from datetime import datetime, timedelta

    old_ts = (datetime.now() - timedelta(hours=48)).isoformat()
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "pathlib.Path.read_text",
            return_value=json.dumps({"host": "1.2.3.4", "timestamp": old_ts}),
        ),
    ):
        assert _get_cache() is None


# ── HTTP probing ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_probe_host_info_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"product_type": "HWE-P1", "serial": "S1"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _probe_host_info("192.168.1.100")
        assert result == {"product_type": "HWE-P1", "serial": "S1"}


@pytest.mark.asyncio
async def test_probe_host_info_non_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _probe_host_info("192.168.1.100")
        assert result is None


@pytest.mark.asyncio
async def test_probe_host_info_exception():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=Exception("Connection error"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _probe_host_info("192.168.1.100")
        assert result is None


# ── Host probing ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_probe_host_returns_true():
    with patch(
        "homewizard_cli.discovery._probe_host_info",
        return_value={"product_type": "HWE-P1"},
    ):
        result = await _probe_host("192.168.1.100")
        assert result is True


@pytest.mark.asyncio
async def test_probe_host_returns_false():
    with patch(
        "homewizard_cli.discovery._probe_host_info",
        return_value={"product_type": "HWE-SKT"},
    ):
        result = await _probe_host("192.168.1.100")
        assert result is False


# ── discover_host ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_discover_host_use_cache_false_skips_cache():
    with (
        patch("homewizard_cli.discovery._get_cache") as mock_get_cache,
        patch(
            "homewizard_cli.discovery.discover_mdns_v2",
            return_value="192.168.1.100",
        ),
        patch("homewizard_cli.discovery._save_cache"),
    ):
        host, from_cache = await discover_host(use_cache=False)
        assert host == "192.168.1.100"
        assert from_cache is False
        mock_get_cache.assert_not_called()
