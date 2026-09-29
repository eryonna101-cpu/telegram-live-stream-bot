from __future__ import annotations

from aiogram.types import CallbackQuery, Message

from app_context import AppContext
from utils.helpers import format_datetime
from utils.security import is_owner


def owner_from_message(message: Message, ctx: AppContext) -> bool:
    return is_owner(message.from_user.id if message.from_user else None, ctx.config.owner_id)


def owner_from_callback(query: CallbackQuery, ctx: AppContext) -> bool:
    return is_owner(query.from_user.id if query.from_user else None, ctx.config.owner_id)


async def deny_message(message: Message) -> None:
    await message.answer("❌ غير مصرح لك باستخدام هذا البوت.")


async def deny_callback(query: CallbackQuery) -> None:
    await query.answer("غير مصرح لك", show_alert=True)


async def main_text(ctx: AppContext) -> str:
    status = await ctx.database.get_stream_status()
    settings = await ctx.database.get_settings()
    current = "لا يوجد"
    if status.get("current_video_id"):
        video = await ctx.database.get_video(str(status["current_video_id"]))
        current = str(video.get("filename", "لا يوجد")) if video else "لا يوجد"
    channel = str(settings.get("channel_id") or ctx.config.channel_id)
    mode = "Playlist" if status.get("mode") == "PLAYLIST" else "Loop"
    started = format_datetime(status.get("started_at"))
    return (
        "🎥 بوت البث المباشر\n\n"
        f"🟢 حالة البث: {status.get('status', 'STOPPED')}\n"
        f"📺 القناة: {channel}\n"
        f"🎬 الفيديو الحالي: {current}\n"
        f"⏱ بدأ منذ: {started}\n"
        f"🔁 الوضع: {mode}"
    )


async def show_home_message(message: Message, ctx: AppContext) -> None:
    from keyboards.main import main_keyboard

    await message.answer(await main_text(ctx), reply_markup=main_keyboard())


async def show_home_callback(query: CallbackQuery, ctx: AppContext) -> None:
    from keyboards.main import main_keyboard

    await query.message.edit_text(await main_text(ctx), reply_markup=main_keyboard())
    await query.answer()