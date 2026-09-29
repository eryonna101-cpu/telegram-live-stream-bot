from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def videos_keyboard(videos: list[dict], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"🎬 {video.get('filename', 'فيديو')[:36]}",
                callback_data=f"video:view:{video['id']}",
            )
        ]
        for video in videos
    ]
    pagination: list[InlineKeyboardButton] = []
    if page > 0:
        pagination.append(
            InlineKeyboardButton(text="◀️ السابق", callback_data=f"videos:list:{page - 1}")
        )
    if has_next:
        pagination.append(
            InlineKeyboardButton(text="التالي ▶️", callback_data=f"videos:list:{page + 1}")
        )
    if pagination:
        rows.append(pagination)
    rows.append([InlineKeyboardButton(text="⬅️ رجوع", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def video_detail_keyboard(video_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ تشغيل الآن", callback_data=f"video:play:{video_id}")],
            [
                InlineKeyboardButton(
                    text="➕ إضافة للـPlaylist", callback_data=f"playlist:add:{video_id}"
                )
            ],
            [InlineKeyboardButton(text="🗑 حذف", callback_data=f"video:delete:{video_id}")],
            [InlineKeyboardButton(text="⬅️ رجوع", callback_data="videos:list:0")],
        ]
    )


def delete_confirm_keyboard(video_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ نعم، احذف", callback_data=f"video:delete_yes:{video_id}"),
                InlineKeyboardButton(text="❌ إلغاء", callback_data=f"video:view:{video_id}"),
            ]
        ]
    )