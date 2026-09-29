from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ تشغيل البث", callback_data="stream:start"),
                InlineKeyboardButton(text="⏸ إيقاف مؤقت", callback_data="stream:pause"),
            ],
            [
                InlineKeyboardButton(text="⏹ إيقاف البث", callback_data="stream:stop"),
                InlineKeyboardButton(text="🔄 إعادة تشغيل", callback_data="stream:restart"),
            ],
            [
                InlineKeyboardButton(text="📤 رفع فيديو", callback_data="upload:start"),
                InlineKeyboardButton(text="📁 الفيديوهات", callback_data="videos:list:0"),
            ],
            [
                InlineKeyboardButton(text="📋 Playlist", callback_data="playlist:view"),
                InlineKeyboardButton(text="📊 الإحصائيات", callback_data="stats:view"),
            ],
            [
                InlineKeyboardButton(text="⚙️ الإعدادات", callback_data="settings:view"),
                InlineKeyboardButton(text="🔄 تحديث", callback_data="menu:refresh"),
            ],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ رجوع", callback_data="menu:home")]
        ]
    )