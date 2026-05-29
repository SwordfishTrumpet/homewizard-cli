"""Alert action dispatcher for --alert-webhook, --alert-cmd, --alert-cooldown."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone

log = logging.getLogger(__name__)


class AlertDispatcher:
    def __init__(
        self,
        webhook_urls: list[str] | None = None,
        commands: list[str] | None = None,
        cooldown_seconds: float = 0.0,
    ):
        self._webhook_urls = webhook_urls or []
        self._commands = commands or []
        self._cooldown = cooldown_seconds
        self._last_fired: float = 0.0

    @property
    def configured(self) -> bool:
        return bool(self._webhook_urls or self._commands)

    def _should_fire(self) -> bool:
        if not self.configured:
            return False
        if self._cooldown <= 0:
            return True
        return time.monotonic() - self._last_fired >= self._cooldown

    def _mark_fired(self) -> None:
        self._last_fired = time.monotonic()

    async def dispatch(self, condition: str, data: dict) -> None:
        if not self._should_fire():
            return
        self._mark_fired()

        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {"timestamp": timestamp, "condition": condition, "data": data}
        tasks: list[asyncio.Task] = []

        for url in self._webhook_urls:
            tasks.append(asyncio.create_task(self._post_webhook(url, payload)))
        for cmd in self._commands:
            tasks.append(asyncio.create_task(self._run_command(cmd, payload)))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.warning("Alert dispatch failed: %s", result)

    async def _post_webhook(self, url: str, payload: dict) -> None:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
        except Exception as e:
            log.warning("Alert webhook %s failed: %s", url, e)

    async def _run_command(self, cmd: str, payload: dict) -> None:
        env: dict[str, str] = {}
        env.update(os.environ)
        env["HW_CONDITION"] = payload["condition"]
        env["HW_DATA"] = json.dumps(payload["data"])
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                env=env,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            log.warning("Alert command '%s' failed: %s", cmd, e)
