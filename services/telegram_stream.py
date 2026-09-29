from __future__ import annotations

import logging
from typing import Any

from pyrogram import Client


class TelegramStreamService:
    """Optional user-client bridge for channel metadata and access validation.

    Telegram's RTMP key is intentionally configured by the owner. The Bot API and
    Pyrogram do not safely expose a universal key-retrieval flow for every channel
    type, so the service never logs or guesses it.
    """

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str,
        channel_id: str,
        logger: logging.Logger,
    ) -> None:
        self.channel_id = channel_id
        self.log = logger.getChild("telegram")
        self.client = Client(session_name, api_id=api_id, api_hash=api_hash)

    async def channel_title(self) -> str:
        try:
            async with self.client:
                chat = await self.client.get_chat(self.channel_id)
                return chat.title or str(self.channel_id)
        except Exception as exc:
            self.log.warning("Channel metadata lookup failed: %s", exc)
            return str(self.channel_id)

    async def validate_channel_access(self) -> dict[str, Any]:
        try:
            async with self.client:
                chat = await self.client.get_chat(self.channel_id)
                return {"ok": True, "title": chat.title, "id": chat.id}
        except Exception as exc:
            self.log.error("Telegram channel validation failed: %s", exc)
            return {"ok": False, "error": str(exc)}