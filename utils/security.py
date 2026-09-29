from __future__ import annotations

import re
from pathlib import Path


def is_owner(user_id: int | None, owner_id: int) -> bool:
    return user_id is not None and user_id == owner_id


def safe_filename(filename: str, extension: str) -> str:
    """Return a display-safe basename with a controlled extension."""
    basename = Path(filename or "video").name
    basename = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._") or "video"
    suffix = extension.lower()
    if suffix not in {".mp4", ".mkv", ".mov", ".avi", ".webm"}:
        suffix = ".mp4"
    if not basename.lower().endswith(suffix):
        basename = f"{Path(basename).stem}{suffix}"
    return basename


def redact_secret(value: str | None, visible: int = 4) -> str:
    if not value:
        return "غير مضبوط"
    if len(value) <= visible:
        return "•" * len(value)
    return f"{'•' * max(8, len(value) - visible)}{value[-visible:]}"