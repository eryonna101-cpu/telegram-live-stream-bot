from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Database:
    """MongoDB repository. Documents use stable string IDs for callback safety."""

    def __init__(self, uri: str, database_name: str, logger: logging.Logger) -> None:
        self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10_000)
        self.db = self.client[database_name]
        self.log = logger.getChild("database")

    async def connect(self) -> None:
        await self.client.admin.command("ping")
        await self.db.videos.create_index("created_at")
        await self.db.playlists.create_index("is_active")
        await self.db.users.create_index("telegram_id", unique=True)
        await self.db.playlist_items.create_index(
            [("playlist_id", 1), ("position", 1)], unique=True
        )
        await self.db.logs.create_index("created_at")
        if await self.db.settings.count_documents({"_id": "singleton"}) == 0:
            await self.db.settings.insert_one(
                {
                    "_id": "singleton",
                    "channel_id": "",
                    "rtmp_url": None,
                    "stream_key": None,
                    "video_bitrate": "2500k",
                    "audio_bitrate": "128k",
                    "resolution": "1280x720",
                    "fps": 30,
                    "preset": "veryfast",
                }
            )
        if await self.db.stream_status.count_documents({"_id": "singleton"}) == 0:
            await self.db.stream_status.insert_one(
                {
                    "_id": "singleton",
                    "status": "STOPPED",
                    "mode": "LOOP",
                    "current_video_id": None,
                    "current_playlist_id": None,
                    "started_at": None,
                    "restart_count": 0,
                    "last_error": None,
                    "should_run": False,
                }
            )

    async def close(self) -> None:
        self.client.close()

    async def upsert_user(self, telegram_id: int, username: str | None = None) -> None:
        await self.db.users.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {"username": username, "last_seen_at": utc_now()},
                "$setOnInsert": {"telegram_id": telegram_id, "created_at": utc_now()},
            },
            upsert=True,
        )

    @staticmethod
    def _without_id(document: dict[str, Any] | None) -> dict[str, Any] | None:
        if document is None:
            return None
        document.pop("_id", None)
        return document

    async def get_settings(self) -> dict[str, Any]:
        document = await self.db.settings.find_one({"_id": "singleton"})
        return self._without_id(document) or {}

    async def update_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        await self.db.settings.update_one(
            {"_id": "singleton"}, {"$set": values}, upsert=True
        )
        return await self.get_settings()

    async def get_stream_status(self) -> dict[str, Any]:
        document = await self.db.stream_status.find_one({"_id": "singleton"})
        return self._without_id(document) or {}

    async def update_stream_status(self, values: dict[str, Any]) -> dict[str, Any]:
        await self.db.stream_status.update_one(
            {"_id": "singleton"}, {"$set": values}, upsert=True
        )
        return await self.get_stream_status()

    async def add_video(self, values: dict[str, Any]) -> dict[str, Any]:
        document = {"id": str(uuid.uuid4()), "created_at": utc_now(), **values}
        await self.db.videos.insert_one(document)
        return self._without_id(document) or {}

    async def get_video(self, video_id: str) -> dict[str, Any] | None:
        return self._without_id(await self.db.videos.find_one({"id": video_id}))

    async def list_videos(self, skip: int = 0, limit: int = 10) -> list[dict[str, Any]]:
        cursor = self.db.videos.find().sort("created_at", -1).skip(skip).limit(limit)
        return [self._without_id(item) or {} async for item in cursor]

    async def count_videos(self) -> int:
        return await self.db.videos.count_documents({})

    async def delete_video(self, video_id: str) -> bool:
        result = await self.db.videos.delete_one({"id": video_id})
        await self.db.playlists.update_many({}, {"$pull": {"video_ids": video_id}})
        return result.deleted_count == 1

    async def get_active_playlist(self) -> dict[str, Any] | None:
        return self._without_id(await self.db.playlists.find_one({"is_active": True}))

    async def get_playlist(self, playlist_id: str) -> dict[str, Any] | None:
        return self._without_id(await self.db.playlists.find_one({"id": playlist_id}))

    async def list_playlists(self) -> list[dict[str, Any]]:
        cursor = self.db.playlists.find().sort("created_at", 1)
        return [self._without_id(item) or {} async for item in cursor]

    async def create_playlist(self, name: str) -> dict[str, Any]:
        document = {
            "id": str(uuid.uuid4()),
            "name": name,
            "video_ids": [],
            "created_at": utc_now(),
            "is_active": True,
        }
        await self.db.playlists.update_many({}, {"$set": {"is_active": False}})
        await self.db.playlists.insert_one(document)
        return self._without_id(document) or {}

    async def add_video_to_playlist(self, playlist_id: str, video_id: str) -> bool:
        result = await self.db.playlists.update_one(
            {"id": playlist_id, "video_ids": {"$ne": video_id}},
            {"$push": {"video_ids": video_id}},
        )
        if result.modified_count == 1:
            playlist = await self.get_playlist(playlist_id)
            if playlist:
                await self.db.playlist_items.insert_one(
                    {
                        "playlist_id": playlist_id,
                        "video_id": video_id,
                        "position": len(playlist.get("video_ids", [])) - 1,
                    }
                )
        return result.modified_count == 1

    async def remove_video_from_playlist(self, playlist_id: str, video_id: str) -> bool:
        result = await self.db.playlists.update_one(
            {"id": playlist_id}, {"$pull": {"video_ids": video_id}}
        )
        if result.modified_count == 1:
            await self.db.playlist_items.delete_one(
                {"playlist_id": playlist_id, "video_id": video_id}
            )
            playlist = await self.get_playlist(playlist_id)
            if playlist:
                await self._rewrite_playlist_items(playlist_id, playlist.get("video_ids", []))
        return result.modified_count == 1

    async def move_playlist_item(
        self, playlist_id: str, video_id: str, direction: int
    ) -> bool:
        playlist = await self.get_playlist(playlist_id)
        if not playlist:
            return False
        ids = list(playlist.get("video_ids", []))
        try:
            index = ids.index(video_id)
        except ValueError:
            return False
        target = index + direction
        if target < 0 or target >= len(ids):
            return False
        ids[index], ids[target] = ids[target], ids[index]
        await self.db.playlists.update_one(
            {"id": playlist_id}, {"$set": {"video_ids": ids}}
        )
        await self._rewrite_playlist_items(playlist_id, ids)
        return True

    async def _rewrite_playlist_items(self, playlist_id: str, video_ids: list[str]) -> None:
        await self.db.playlist_items.delete_many({"playlist_id": playlist_id})
        if video_ids:
            await self.db.playlist_items.insert_many(
                [
                    {"playlist_id": playlist_id, "video_id": video_id, "position": position}
                    for position, video_id in enumerate(video_ids)
                ]
            )

    async def write_log(self, level: str, message: str, context: dict[str, Any] | None = None) -> None:
        await self.db.logs.insert_one(
            {"level": level, "message": message, "context": context or {}, "created_at": utc_now()}
        )