from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FFmpegOptions:
    resolution: str = "1280x720"
    fps: int = 30
    video_bitrate: str = "2500k"
    audio_bitrate: str = "128k"
    preset: str = "veryfast"


class FFmpegService:
    def __init__(self, logger: logging.Logger) -> None:
        self.log = logger.getChild("ffmpeg")

    @staticmethod
    def output_url(rtmp_url: str, stream_key: str) -> str:
        separator = "&" if "?" in rtmp_url else "/"
        return f"{rtmp_url.rstrip('/')}{separator}{stream_key}"

    def command(
        self, video_path: Path, rtmp_url: str, stream_key: str, options: FFmpegOptions
    ) -> list[str]:
        width, height = (part.strip() for part in options.resolution.lower().split("x", 1))
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={options.fps},format=yuv420p"
        )
        return [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "warning",
            "-re",
            "-i",
            str(video_path),
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            options.preset,
            "-tune",
            "zerolatency",
            "-b:v",
            options.video_bitrate,
            "-maxrate",
            options.video_bitrate,
            "-bufsize",
            "2M",
            "-g",
            str(options.fps * 2),
            "-keyint_min",
            str(options.fps),
            "-sc_threshold",
            "0",
            "-c:a",
            "aac",
            "-b:a",
            options.audio_bitrate,
            "-ar",
            "44100",
            "-ac",
            "2",
            "-f",
            "flv",
            self.output_url(rtmp_url, stream_key),
        ]

    async def spawn(
        self, video_path: Path, rtmp_url: str, stream_key: str, options: FFmpegOptions
    ) -> asyncio.subprocess.Process:
        command = self.command(video_path, rtmp_url, stream_key, options)
        self.log.info("Starting FFmpeg for %s", video_path.name)
        return await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )