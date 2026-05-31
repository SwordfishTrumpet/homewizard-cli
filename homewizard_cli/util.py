"""Shared utilities for homewizard-cli."""

from datetime import datetime


def _crc16(data: bytes) -> int:
    """Compute CRC16-IBM (CRC-16/ARC) checksum."""
    crc = 0x0000
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_p1_timestamp(ts: int | str | None, fmt: str | None = None) -> str:
    try:
        s = str(ts).zfill(12)
        dt = datetime(
            2000 + int(s[0:2]),
            int(s[2:4]),
            int(s[4:6]),
            int(s[6:8]),
            int(s[8:10]),
            int(s[10:12]),
        )
        return dt.strftime(fmt or DEFAULT_TIMESTAMP_FORMAT)
    except (ValueError, IndexError):
        return str(ts)
