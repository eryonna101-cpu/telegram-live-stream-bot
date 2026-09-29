from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SecretRedactionFilter(logging.Filter):
    _patterns = (
        re.compile(r"(BOT_TOKEN=|API_HASH=|STREAM_KEY=)(\S+)", re.IGNORECASE),
        re.compile(r"(rtmp://[^/]+/)(\S+)", re.IGNORECASE),
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in self._patterns:
            message = pattern.sub(r"\1[REDACTED]", message)
        record.msg = message
        record.args = ()
        return True


def configure_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("telegram_live_bot")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    redaction = SecretRedactionFilter()
    for filename, level in (
        ("bot.log", logging.INFO),
        ("ffmpeg.log", logging.INFO),
        ("errors.log", logging.ERROR),
    ):
        handler = RotatingFileHandler(
            log_dir / filename, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        handler.addFilter(redaction)
        logger.addHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(redaction)
    logger.addHandler(console)
    return logger