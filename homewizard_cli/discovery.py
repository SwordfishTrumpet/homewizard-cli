"""Device discovery for HomeWizard P1 Meter."""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta

import httpx
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener

from .errors import DeviceNotFoundError


CACHE_DIR = Path.home() / ".config" / "homewizard-cli"
CACHE_FILE = CACHE_DIR / "host"
CACHE_TTL = timedelta(hours=24)


def _get_cache() -> str | None:
    """Read cached host IP if not expired."""
    if not CACHE_FILE.exists():
        return None

    try:
        data = json.loads(CACHE_FILE.read_text())
        timestamp = datetime.fromisoformat(data["timestamp"])
        if datetime.now() - timestamp < CACHE_TTL:
            return data["host"]
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    return None


def _save_cache(host: str):
    """Save host IP to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "host": host,
        "timestamp": datetime.now().isoformat(),
    }
    CACHE_FILE.write_text(json.dumps(data))


class _HostListener(ServiceListener):
    """Zeroconf listener for HomeWizard devices."""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            ip = ".".join(str(b) for b in info.addresses[0])
            props = {}
            if info.properties:
                props = {
                    k.decode() if isinstance(k, bytes) else k: v.decode()
                    if isinstance(v, bytes)
                    else v
                    for k, v in info.properties.items()
                }
            self.entries.append(
                {"ip": ip, "name": name, "properties": props, "host": ip}
            )

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


V1_MDNS_SERVICE = "_hwenergy._tcp.local."
V2_MDNS_SERVICE = "_homewizard._tcp.local."


async def _discover_mdns_for(service: str, timeout: float = 2.0) -> str | None:
    """Discover first device via given mDNS service."""
    zeroconf = Zeroconf()
    listener = _HostListener()
    browser = ServiceBrowser(zeroconf, service, listener)
    await asyncio.sleep(timeout)
    browser.cancel()
    zeroconf.close()
    if listener.entries:
        return listener.entries[0]["ip"]
    return None


async def _discover_all_mdns_for(service: str, timeout: float = 2.0) -> list[dict]:
    """Discover all devices via given mDNS service."""
    zeroconf = Zeroconf()
    listener = _HostListener()
    ServiceBrowser(zeroconf, service, listener)
    await asyncio.sleep(timeout)
    zeroconf.close()
    return listener.entries


async def discover_mdns(timeout: float = 2.0) -> str | None:
    """Discover P1 meter via v1 mDNS."""
    return await _discover_mdns_for(V1_MDNS_SERVICE, timeout)


async def discover_all_mdns(timeout: float = 2.0) -> list[dict]:
    """Discover all v1 HomeWizard devices via mDNS."""
    return await _discover_all_mdns_for(V1_MDNS_SERVICE, timeout)


async def discover_mdns_v2(timeout: float = 2.0) -> str | None:
    """Discover v2 device via _homewizard._tcp mDNS."""
    return await _discover_mdns_for(V2_MDNS_SERVICE, timeout)


async def discover_all_mdns_v2(timeout: float = 2.0) -> list[dict]:
    """Discover all v2 HomeWizard devices via mDNS."""
    return await _discover_all_mdns_for(V2_MDNS_SERVICE, timeout)


async def _probe_host_info(
    host: str, timeout: float = 1.0, use_https: bool = False
) -> dict | None:
    """Probe host and return device info dict, or None if not a valid device."""
    protocol = "https" if use_https else "http"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout), verify=False
        ) as client:
            resp = await client.get(f"{protocol}://{host}/api/")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def discover_all_hosts(timeout: float = 3.0) -> list[dict]:
    """Discover all HomeWizard devices (v1 + v2) and return their info."""
    entries = await discover_all_mdns(timeout=2.0)
    entries += await discover_all_mdns_v2(timeout=2.0)
    seen = set()
    results = []
    for entry in entries:
        ip = entry["ip"]
        if ip in seen:
            continue
        seen.add(ip)
        info = await _probe_host_info(ip, timeout=1.0)
        if not info:
            info = await _probe_host_info(ip, timeout=1.0, use_https=True)
        if info:
            results.append(
                {
                    "host": ip,
                    "product_type": info.get("product_type", "Unknown"),
                    "serial": info.get("serial", ""),
                    "product_name": info.get("product_name", "Unknown"),
                }
            )
    return results


async def _probe_host(host: str, timeout: float = 1.0) -> bool:
    """Check if host is a valid P1 meter."""
    info = await _probe_host_info(host, timeout)
    return info is not None and info.get("product_type") == "HWE-P1"


async def discover_arp(timeout: float = 3.0) -> str | None:
    """Fallback: scan ARP table for known MAC prefixes."""
    try:
        with open("/proc/net/arp") as f:
            lines = f.readlines()[1:]

        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                ip = parts[0]
                mac = parts[3]
                if mac.startswith("5c:62:8b") or mac.startswith("3c:61:05"):
                    if await _probe_host(ip, timeout=1.0):
                        return ip
    except (FileNotFoundError, PermissionError):
        pass
    return None


async def discover_host(
    explicit_host: str | None = None,
    use_cache: bool = True,
    timeout: float = 3.0,
) -> tuple[str, bool]:
    """Resolve host IP using multiple strategies. Returns (host, from_cache)."""

    # 1. Explicit host
    if explicit_host:
        return explicit_host, False

    # 2. Cache
    if use_cache:
        cached = _get_cache()
        if cached:
            return cached, True

    # 3. mDNS discovery (v2 preferred)
    host = await discover_mdns_v2(timeout=2.0)
    if host:
        _save_cache(host)
        return host, False

    # 4. mDNS discovery (v1 fallback)
    host = await discover_mdns(timeout=2.0)
    if host:
        _save_cache(host)
        return host, False

    # 5. ARP fallback
    host = await discover_arp(timeout=timeout)
    if host:
        _save_cache(host)
        return host, False

    # 6. All failed
    raise DeviceNotFoundError(
        "Could not find P1 Meter",
        "mDNS discovery (v1+v2) and ARP scan both failed. Use --host to specify IP.",
    )
