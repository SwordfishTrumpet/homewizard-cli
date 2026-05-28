"""Shared utilities for homewizard-cli."""

from datetime import datetime


def format_p1_timestamp(ts: int) -> str:
    """Convert P1 compact timestamp YYMMDDHHmmSS to ISO string."""
    try:
        s = str(ts)
        if len(s) >= 12:
            dt = datetime(
                2000 + int(s[0:2]),
                int(s[2:4]),
                int(s[4:6]),
                int(s[6:8]),
                int(s[8:10]),
                int(s[10:12]),
            )
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        pass
    return str(ts)
