"""Device discovery for HomeWizard P1 Meter."""

import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

import httpx
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener

from .errors import DeviceNotFoundError


CACHE_DIR = Path.home() / ".config" / "homewizard-cli"
CACHE_FILE = CACHE_DIR / "host"
CACHE_TTL = timedelta(hours=24)


def _get_cache() -> Optional[str]:
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


class _MdnsListener(ServiceListener):
    """Zeroconf listener for HomeWizard devices."""

    def __init__(self):
        self.hosts = []

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            ip = ".".join(str(b) for b in info.addresses[0])
            self.hosts.append(ip)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


async def discover_mdns(timeout: float = 2.0) -> Optional[str]:
    """Discover P1 meter via mDNS."""
    zeroconf = Zeroconf()
    listener = _MdnsListener()

    browser = ServiceBrowser(zeroconf, "_hwenergy._tcp.local.", listener)

    await asyncio.sleep(timeout)

    browser.cancel()
    zeroconf.close()

    if listener.hosts:
        return listener.hosts[0]
    return None


async def _probe_host(host: str, timeout: float = 1.0) -> bool:
    """Check if host is a valid P1 meter."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            resp = await client.get(f"http://{host}/api/")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("product_type") == "HWE-P1"
    except Exception:
        pass
    return False


async def discover_arp(timeout: float = 3.0) -> Optional[str]:
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
    explicit_host: Optional[str] = None,
    use_cache: bool = True,
    timeout: float = 3.0,
) -> str:
    """Resolve host IP using multiple strategies."""

    # 1. Explicit host
    if explicit_host:
        return explicit_host

    # 2. Cache
    if use_cache:
        cached = _get_cache()
        if cached:
            return cached

    # 3. mDNS discovery
    host = await discover_mdns(timeout=2.0)
    if host:
        _save_cache(host)
        return host

    # 4. ARP fallback
    host = await discover_arp(timeout=timeout)
    if host:
        _save_cache(host)
        return host

    # 5. All failed
    raise DeviceNotFoundError(
        "Could not find P1 Meter",
        "mDNS discovery and ARP scan both failed. Use --host to specify IP.",
    )
