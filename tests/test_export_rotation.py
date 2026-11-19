"""File rotation must never misfile a record (issue #20).

A record written after a period boundary belongs in the current period file. When
the rotation itself fails - a rename that errors once, or a reopen that fails
after the rename - the exporter used to advance its rotation key anyway and keep
appending through the handle that now named the old period.
"""

import asyncio
import pathlib
import tempfile
from datetime import datetime as RealDatetime
from unittest.mock import AsyncMock, patch

from homewizard_cli.commands.export import _export_async
from homewizard_cli.models import Measurement

REAL_OPEN = pathlib.Path.open
REAL_RENAME = pathlib.Path.rename


class FakeClock:
    def __init__(self, times):
        self.times = list(times)

    def now(self):
        return self.times.pop(0) if len(self.times) > 1 else self.times[0]


async def _no_wait(fut, timeout=None):
    if asyncio.iscoroutine(fut):
        fut.close()
    raise TimeoutError


def _make_client(values):
    iterator = iter(values)

    async def measurement(endpoint, model):
        try:
            return Measurement(active_power_w=next(iterator))
        except StopIteration:
            raise RuntimeError("stop") from None

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get_json_v2 = AsyncMock(side_effect=measurement)
    return client


async def _export_to(target, clock, values, open_patch=None, rename_patch=None):
    patches = [
        patch(
            "homewizard_cli.commands.export.resolve_client",
            return_value=_make_client(values),
        ),
        patch("homewizard_cli.commands.export.datetime", clock),
        patch("homewizard_cli.commands.export.asyncio.wait_for", side_effect=_no_wait),
    ]
    if open_patch is not None:
        patches.append(patch.object(pathlib.Path, "open", open_patch))
    if rename_patch is not None:
        patches.append(patch.object(pathlib.Path, "rename", rename_patch))
    for p in patches:
        p.start()
    try:
        try:
            await _export_async(
                format="json",
                watch=0.01,
                file=str(target),
                host="127.0.0.1",
                request_timeout=1.0,
                rotate="daily",
            )
        except RuntimeError:
            pass
    finally:
        for p in reversed(patches):
            p.stop()


DAYS = (
    RealDatetime(2026, 5, 29, 10, 0, 0),
    RealDatetime(2026, 5, 30, 10, 0, 0),
    RealDatetime(2026, 5, 31, 10, 0, 0),
)


def _read(path):
    return path.read_text() if path.exists() else ""


def test_reopen_failure_keeps_the_current_file_and_misfiles_nothing():
    """A reopen that keeps failing must not leave later records in the archive."""
    directory = pathlib.Path(tempfile.mkdtemp())
    target = directory / "export.json"
    opens = {"n": 0}

    def open_fails_after_start(self, *args, **kwargs):
        if self == target:
            opens["n"] += 1
            if opens["n"] >= 2:
                raise OSError(13, "simulated EACCES after rotation", str(self))
        return REAL_OPEN(self, *args, **kwargs)

    asyncio.run(
        _export_to(
            target, FakeClock(DAYS), [111.5, 222.5, 333.5], open_patch=open_fails_after_start
        )
    )

    rotated = target.with_name(target.name + ".2026-05-29")
    archived = _read(rotated)
    assert target.exists(), "the current period file must still exist"
    assert "222.5" not in archived
    assert "333.5" not in archived


def test_transient_rename_failure_files_each_day_in_its_own_period():
    """One failed rename is retried, so the 29th keeps only its own record."""
    directory = pathlib.Path(tempfile.mkdtemp())
    target = directory / "export.json"
    renames = {"n": 0}

    def rename_fails_once(self, dst):
        renames["n"] += 1
        if renames["n"] == 1:
            raise OSError(16, "simulated transient rename failure", str(dst))
        return REAL_RENAME(self, dst)

    asyncio.run(
        _export_to(
            target,
            FakeClock(DAYS),
            [111.5, 222.5, 333.5],
            rename_patch=rename_fails_once,
        )
    )

    day29 = target.with_name(target.name + ".2026-05-29")
    day30 = target.with_name(target.name + ".2026-05-30")
    assert day29.exists()
    assert "111.5" in _read(day29)
    assert "111.5" not in _read(day30)
