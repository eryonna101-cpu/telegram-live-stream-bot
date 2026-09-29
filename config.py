from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _int_env(name: str, default: int | None = None) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        if default is None:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    api_id: int
    api_hash: str
    mongo_uri: str
    mongo_database: str
    channel_id: str
    rtmp_url: str | None
    stream_key: str | None
    pyrogram_session_name: str
    video_dir: Path
    log_dir: Path
    max_video_size_gb: float
    low_storage_gb: float
    ffmpeg_restart_limit: int
    ffmpeg_restart_delay: int
    video_bitrate: str
    audio_bitrate: str
    resolution: str
    fps: int
    ffmpeg_preset: str

    @property
    def video_extensions(self) -> tuple[str, ...]:
        return (".mp4", ".mkv", ".mov", ".avi", ".webm")


def load_config() -> Config:
    load_dotenv()
    config = Config(
        bot_token=_required("BOT_TOKEN"),
        owner_id=_int_env("OWNER_ID"),
        api_id=_int_env("API_ID"),
        api_hash=_required("API_HASH"),
        mongo_uri=_required("MONGO_URI"),
        mongo_database=os.getenv("MONGO_DATABASE", "telegram_live_bot").strip()
        or "telegram_live_bot",
        channel_id=_required("CHANNEL_ID"),
        rtmp_url=os.getenv("RTMP_URL", "").strip() or None,
        stream_key=os.getenv("STREAM_KEY", "").strip() or None,
        pyrogram_session_name=os.getenv(
            "PYROGRAM_SESSION_NAME", "sessions/telegram_client"
        ).strip()
        or "sessions/telegram_client",
        video_dir=Path(os.getenv("VIDEO_DIR", "videos")),
        log_dir=Path(os.getenv("LOG_DIR", "logs")),
        max_video_size_gb=float(os.getenv("MAX_VIDEO_SIZE_GB", "0")),
        low_storage_gb=float(os.getenv("LOW_STORAGE_GB", "10")),
        ffmpeg_restart_limit=_int_env("FFMPEG_RESTART_LIMIT", 5),
        ffmpeg_restart_delay=_int_env("FFMPEG_RESTART_DELAY", 5),
        video_bitrate=os.getenv("VIDEO_BITRATE", "2500k"),
        audio_bitrate=os.getenv("AUDIO_BITRATE", "128k"),
        resolution=os.getenv("RESOLUTION", "1280x720"),
        fps=_int_env("FPS", 30),
        ffmpeg_preset=os.getenv("FFMPEG_PRESET", "veryfast"),
    )
    if "x" not in config.resolution.lower():
        raise RuntimeError("RESOLUTION must use WIDTHxHEIGHT format")
    if config.fps < 1 or config.fps > 120:
        raise RuntimeError("FPS must be between 1 and 120")
    for directory in (config.video_dir, config.log_dir, Path(config.pyrogram_session_name).parent):
        directory.mkdir(parents=True, exist_ok=True)
    return config