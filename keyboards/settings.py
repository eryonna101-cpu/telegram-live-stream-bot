from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def settings_keyboard(key_visible: bool = False) -> InlineKeyboardMarkup:
    key_label = "🙈 إخفاء المفتاح" if key_visible else "👁 عرض المفتاح"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📺 تعديل Channel ID", callback_data="settings:edit:channel_id")],
            [InlineKeyboardButton(text="🔗 تعديل RTMP URL", callback_data="settings:edit:rtmp_url")],
            [InlineKeyboardButton(text="🔑 تعديل Stream Key", callback_data="settings:edit:stream_key")],
            [
                InlineKeyboardButton(text="🎥 Video Bitrate", callback_data="settings:edit:video_bitrate"),
                InlineKeyboardButton(text="🔊 Audio Bitrate", callback_data="settings:edit:audio_bitrate"),
            ],
            [
                InlineKeyboardButton(text="📐 Resolution", callback_data="settings:edit:resolution"),
                InlineKeyboardButton(text="🎞 FPS", callback_data="settings:edit:fps"),
            ],
            [InlineKeyboardButton(text=key_label, callback_data="settings:toggle_key")],
            [InlineKeyboardButton(text="🗑 إدارة التخزين", callback_data="settings:storage")],
            [InlineKeyboardButton(text="⬅️ رجوع", callback_data="menu:home")],
        ]
    )