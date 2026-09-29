from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def playlist_keyboard(playlist: dict | None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="➕ إضافة فيديو", callback_data="playlist:add_menu"),
            InlineKeyboardButton(text="🆕 Playlist جديدة", callback_data="playlist:new"),
        ]
    ]
    if playlist and playlist.get("video_ids"):
        rows.extend(
            [
                [InlineKeyboardButton(text="▶️ تشغيل Playlist", callback_data="stream:playlist")],
                [InlineKeyboardButton(text="⏹ إيقاف Playlist", callback_data="stream:stop")],
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ رجوع", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def playlist_item_keyboard(playlist_id: str, video_id: str, index: int, total: int) -> InlineKeyboardMarkup:
    movement = []
    if index > 0:
        movement.append(
            InlineKeyboardButton(
                text="⬆️", callback_data=f"playlist:move:{playlist_id}:{video_id}:-1"
            )
        )
    if index < total - 1:
        movement.append(
            InlineKeyboardButton(
                text="⬇️", callback_data=f"playlist:move:{playlist_id}:{video_id}:1"
            )
        )
    rows = [movement] if movement else []
    rows.append(
        [
            InlineKeyboardButton(
                text="🗑 إزالة", callback_data=f"playlist:remove:{playlist_id}:{video_id}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)