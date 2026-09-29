from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BroadcastSettings:
    channel_id: str
    rtmp_url: str | None
    stream_key: str | None
    video_bitrate: str
    audio_bitrate: str
    resolution: str
    fps: int
    preset: str