from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def format_bytes(value: int | float | None) -> str:
    amount = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"


def format_duration(seconds: int | float | None) -> str:
    total = max(0, int(seconds or 0))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_datetime(value: datetime | str | None) -> str:
    if not value:
        return "غير متوفر"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def storage_snapshot(path: Path) -> dict[str, int]:
    usage = __import__("shutil").disk_usage(path)
    return {"total": usage.total, "used": usage.used, "free": usage.free}