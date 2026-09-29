from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from database import Database
from services.ffmpeg import FFmpegOptions, FFmpegService


class StreamController:
    def __init__(
        self,
        database: Database,
        ffmpeg: FFmpegService,
        logger: logging.Logger,
        restart_limit: int,
        restart_delay: int,
        owner_notify: Callable[[str], Awaitable[None]],
    ) -> None:
        self.database = database
        self.ffmpeg = ffmpeg
        self.log = logger.getChild("controller")
        self.restart_limit = restart_limit
        self.restart_delay = restart_delay
        self.owner_notify = owner_notify
        self._task: asyncio.Task[None] | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._stop_requested = asyncio.Event()
        self._lock = asyncio.Lock()
        self._run_requested = False

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(
        self,
        video_id: str | None = None,
        playlist_id: str | None = None,
        mode: str = "LOOP",
    ) -> None:
        async with self._lock:
            if self.is_running:
                await self._stop_locked("تغيير مصدر البث")
            self._stop_requested.clear()
            self._run_requested = True
            self._task = asyncio.create_task(
                self._run(video_id=video_id, playlist_id=playlist_id, mode=mode),
                name="stream-controller",
            )

    async def stop(self, reason: str = "إيقاف يدوي") -> None:
        async with self._lock:
            await self._stop_locked(reason)

    async def restart(
        self,
        video_id: str | None = None,
        playlist_id: str | None = None,
        mode: str = "LOOP",
    ) -> None:
        await self.stop("إعادة تشغيل البث")
        await asyncio.sleep(2)
        await self.start(video_id=video_id, playlist_id=playlist_id, mode=mode)

    async def _stop_locked(self, reason: str) -> None:
        self._run_requested = False
        self._stop_requested.set()
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
        if self._task and not self._task.done() and self._task is not asyncio.current_task():
            try:
                await asyncio.wait_for(self._task, timeout=15)
            except asyncio.TimeoutError:
                self._task.cancel()
        self._task = None
        self._process = None
        await self._set_status(
            status="STOPPED", should_run=False, last_error=reason, current_video_name=None
        )

    async def _run(self, video_id: str | None, playlist_id: str | None, mode: str) -> None:
        settings = await self.database.get_settings()
        rtmp_url = settings.get("rtmp_url")
        stream_key = settings.get("stream_key")
        if not rtmp_url or not stream_key:
            await self._set_status(
                status="ERROR",
                should_run=False,
                last_error="لم يتم ضبط RTMP URL و Stream Key",
                current_video_name=None,
            )
            await self.owner_notify("🚨 تعذر بدء البث\nاضبط RTMP URL و Stream Key من الإعدادات.")
            return

        playlist = await self.database.get_playlist(playlist_id) if playlist_id else None
        next_video_id = video_id
        position = 0
        restarts = 0
        started_at = datetime.now(timezone.utc)
        await self.database.update_stream_status(
            {
                "status": "STARTING",
                "mode": mode,
                "current_video_id": next_video_id,
                "current_playlist_id": playlist_id,
                "started_at": started_at,
                "restart_count": 0,
                "last_error": None,
                "should_run": True,
            }
        )
        await self.owner_notify("🟢 LIVE STREAM STARTED")

        try:
            while self._run_requested and not self._stop_requested.is_set():
                if playlist:
                    ids = list(playlist.get("video_ids", []))
                    if not ids:
                        raise RuntimeError("الـPlaylist فارغة")
                    if next_video_id not in ids:
                        next_video_id = ids[position % len(ids)]
                    else:
                        position = ids.index(next_video_id)
                if not next_video_id:
                    raise RuntimeError("لم يتم اختيار فيديو للبث")

                video = await self.database.get_video(next_video_id)
                if not video:
                    raise RuntimeError("الفيديو المحدد غير موجود")
                video_path = Path(str(video["filepath"])).resolve()
                if not video_path.exists():
                    raise RuntimeError(f"ملف الفيديو غير موجود: {video_path.name}")

                await self._set_status(
                    status="STARTING",
                    should_run=True,
                    current_video_id=next_video_id,
                    current_video_name=str(video.get("filename", video_path.name)),
                    current_playlist_id=playlist_id,
                    started_at=started_at,
                    restart_count=restarts,
                )
                options = FFmpegOptions(
                    resolution=str(settings.get("resolution", "1280x720")),
                    fps=int(settings.get("fps", 30)),
                    video_bitrate=str(settings.get("video_bitrate", "2500k")),
                    audio_bitrate=str(settings.get("audio_bitrate", "128k")),
                    preset=str(settings.get("preset", "veryfast")),
                )
                self._process = await self.ffmpeg.spawn(
                    video_path, str(rtmp_url), str(stream_key), options
                )
                await self._set_status(
                    status="LIVE",
                    should_run=True,
                    current_video_id=next_video_id,
                    current_video_name=str(video.get("filename", video_path.name)),
                    current_playlist_id=playlist_id,
                    started_at=started_at,
                    restart_count=restarts,
                )
                stderr_task = asyncio.create_task(
                    self._consume_stderr(self._process), name="ffmpeg-stderr"
                )
                returncode = await self._process.wait()
                await stderr_task
                self._process = None

                if not self._run_requested or self._stop_requested.is_set():
                    break
                if returncode == 0:
                    restarts = 0
                    await self.owner_notify(f"🎬 انتهى الفيديو: {video.get('filename', '')}")
                    if playlist:
                        position = (position + 1) % len(ids)
                        next_video_id = ids[position]
                        await self.owner_notify(
                            f"⏭ الانتقال للفيديو التالي: {next_video_id}"
                        )
                    else:
                        next_video_id = video["id"]
                    continue

                restarts += 1
                await self._set_status(
                    status="RESTARTING",
                    should_run=True,
                    current_video_id=next_video_id,
                    current_video_name=str(video.get("filename", video_path.name)),
                    current_playlist_id=playlist_id,
                    started_at=started_at,
                    restart_count=restarts,
                    last_error=f"FFmpeg exit code {returncode}",
                )
                await self.owner_notify(
                    f"🚨 Stream Error\nFFmpeg توقف بشكل غير متوقع.\n"
                    f"🔄 محاولة إعادة التشغيل: {restarts}/{self.restart_limit}"
                )
                await asyncio.sleep(min(self.restart_delay * max(restarts, 1), 60))
                if restarts >= self.restart_limit:
                    await self.owner_notify(
                        "⚠️ تجاوز البث عدد محاولات الاستعادة المحدد، "
                        "وسيستمر النظام في المحاولة مع تأخير أطول."
                    )
                    restarts = 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.log.exception("Stream loop failed")
            await self._set_status(
                status="ERROR",
                should_run=False,
                last_error=str(exc),
                current_video_name=None,
            )
            await self.owner_notify(f"🚨 خطأ في البث\n{exc}")
        finally:
            self._process = None
            if not self._run_requested:
                await self._set_status(
                    status="STOPPED", should_run=False, current_video_name=None
                )

    async def _consume_stderr(self, process: asyncio.subprocess.Process) -> None:
        if not process.stderr:
            return
        while True:
            line = await process.stderr.readline()
            if not line:
                return
            text = line.decode(errors="replace").strip()
            if text:
                self.log.info("%s", text)

    async def _set_status(self, **values: Any) -> None:
        await self.database.update_stream_status(values)
