from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Video:
    id: str
    telegram_file_id: str
    filename: str
    filepath: str
    size: int
    duration: float
    format: str
    created_at: datetime