from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

import psutil

from database import Database
from services.storage import StorageService
from utils.helpers import format_bytes, format_duration


class SystemMonitor:
    def __init__(
        self,
        database: Database,
        storage: StorageService,
        logger: logging.Logger,
        low_storage_gb: float,
        owner_notify: Callable[[str], Awaitable[None]],
    ) -> None:
        self.database = database
        self.storage = storage
        self.log = logger.getChild("monitor")
        self.low_storage_gb = low_storage_gb
        self.owner_notify = owner_notify
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    def start(self) -> None:
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="system-monitor")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        warned = False
        while not self._stopping.is_set():
            snapshot = self.storage.snapshot()
            low = snapshot["free"] < self.low_storage_gb * 1024**3
            if low and not warned:
                warned = True
                await self.owner_notify(
                    f"⚠️ مساحة السيرفر منخفضة.\nالمتاح: {format_bytes(snapshot['free'])}"
                )
            if not low:
                warned = False
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=300)
            except asyncio.TimeoutError:
                continue

    async def stats(self) -> dict[str, str]:
        status = await self.database.get_stream_status()
        snapshot = self.storage.snapshot()
        memory = psutil.virtual_memory()
        uptime = ""
        started_at = status.get("started_at")
        if started_at:
            from datetime import datetime, timezone

            if isinstance(started_at, str):
                try:
                    started_at = datetime.fromisoformat(started_at)
                except ValueError:
                    started_at = None
            if started_at:
                started = (
                    started_at
                    if started_at.tzinfo
                    else started_at.replace(tzinfo=timezone.utc)
                )
                uptime = format_duration(
                    (datetime.now(timezone.utc) - started).total_seconds()
                )
        return {
            "status": str(status.get("status", "STOPPED")),
            "video": str(status.get("current_video_name") or "لا يوجد"),
            "uptime": uptime or "00:00:00",
            "restarts": str(status.get("restart_count", 0)),
            "storage": f"{format_bytes(snapshot['used'])} / {format_bytes(snapshot['total'])}",
            "free": format_bytes(snapshot["free"]),
            "ram": f"{format_bytes(memory.used)} / {format_bytes(memory.total)}",
            "cpu": f"{psutil.cpu_percent(interval=None):.0f}%",
            "process": "FFmpeg" if status.get("should_run") else "متوقف",
            "started_at": str(status.get("started_at") or "غير متوفر"),
        }