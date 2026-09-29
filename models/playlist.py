from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Playlist:
    id: str
    name: str
    video_ids: list[str]
    created_at: datetime
    is_active: bool