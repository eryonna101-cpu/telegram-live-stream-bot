from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from aiogram import Bot

from database import Database
from utils.helpers import storage_snapshot
from utils.security import safe_filename


class StorageService:
    def __init__(
        self, bot: Bot, database: Database, video_dir: Path, logger: logging.Logger
    ) -> None:
        self.bot = bot
        self.database = database
        self.video_dir = video_dir
        self.log = logger.getChild("storage")
        self.video_dir.mkdir(parents=True, exist_ok=True)

    async def download_video(
        self, telegram_file_id: str, original_name: str, extension: str
    ) -> tuple[Path, dict[str, Any]]:
        filename = safe_filename(original_name, extension)
        destination = self.video_dir / f"{uuid.uuid4().hex}_{filename}"
        await self.bot.download(telegram_file_id, destination=destination)
        if not destination.exists() or destination.stat().st_size == 0:
            raise RuntimeError("Telegram returned an empty video file")
        metadata = await self.probe(destination)
        return destination, metadata

    async def probe(self, path: Path) -> dict[str, Any]:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,format_name,size",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.decode(errors='replace')[-500:]}")
        data = json.loads(stdout.decode())
        format_data = data.get("format", {})
        video_stream = next(
            (stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"),
            {},
        )
        return {
            "duration": float(format_data.get("duration") or 0),
            "size": int(float(format_data.get("size") or path.stat().st_size)),
            "format": str(format_data.get("format_name") or path.suffix.lstrip(".")),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
        }

    async def delete_file(self, filepath: str) -> None:
        path = Path(filepath).resolve()
        root = self.video_dir.resolve()
        if root not in path.parents:
            raise ValueError("Refusing to delete a file outside the video directory")
        if path.exists():
            path.unlink()

    def snapshot(self) -> dict[str, int]:
        return storage_snapshot(self.video_dir)

    def has_enough_space(self, minimum_gb: float) -> bool:
        return self.snapshot()["free"] >= minimum_gb * 1024**3

    async def remove_old_videos(self) -> int:
        videos = await self.database.list_videos(skip=0, limit=100_000)
        removed = 0
        for video in sorted(videos, key=lambda item: item.get("created_at") or ""):
            try:
                await self.delete_file(str(video["filepath"]))
                await self.database.delete_video(str(video["id"]))
                removed += 1
            except (KeyError, ValueError, OSError) as exc:
                self.log.warning("Could not remove old video %s: %s", video.get("id"), exc)
        return removed