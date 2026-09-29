from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    telegram_id: int
    username: str | None
    created_at: datetime
    last_seen_at: datetime