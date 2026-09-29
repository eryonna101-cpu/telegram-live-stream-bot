from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app_context import AppContext
from handlers.common import deny_callback, deny_message, owner_from_callback, owner_from_message
from keyboards.main import back_keyboard
from keyboards.settings import settings_keyboard
from utils.helpers import format_bytes
from utils.security import redact_secret


class SettingsStates(StatesGroup):
    waiting_value = State()


def get_router(ctx: AppContext) -> Router:
    router = Router(name="settings")
    visible_key = False

    async def render(query_or_message: CallbackQuery | Message) -> None:
        settings = await ctx.database.get_settings()
        rtmp_url = settings.get("rtmp_url") or "غير مضبوط"
        stream_key = settings.get("stream_key")
        text = (
            "⚙️ إعدادات البث\n\n"
            f"📺 Channel ID: {settings.get('channel_id') or ctx.config.channel_id}\n"
            f"🔗 RTMP URL: {rtmp_url}\n"
            f"🔑 Stream Key: {stream_key if visible_key else redact_secret(stream_key)}\n"
            f"🎞 Video Bitrate: {settings.get('video_bitrate', '2500k')}\n"
            f"🔊 Audio Bitrate: {settings.get('audio_bitrate', '128k')}\n"
            f"📐 Resolution: {settings.get('resolution', '1280x720')}\n"
            f"🎞 FPS: {settings.get('fps', 30)}"
        )
        keyboard = settings_keyboard(visible_key)
        if isinstance(query_or_message, CallbackQuery):
            await query_or_message.message.edit_text(text, reply_markup=keyboard)
        else:
            await query_or_message.answer(text, reply_markup=keyboard)

    @router.callback_query(F.data == "settings:view")
    async def view_settings(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        await render(query)
        await query.answer()

    @router.callback_query(F.data == "settings:toggle_key")
    async def toggle_key(query: CallbackQuery) -> None:
        nonlocal visible_key
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        visible_key = not visible_key
        await render(query)
        await query.answer()

    @router.callback_query(F.data == "settings:storage")
    async def storage_settings(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        snapshot = ctx.storage.snapshot()
        await query.message.edit_text(
            "💾 إدارة التخزين\n\n"
            f"الإجمالي: {format_bytes(snapshot['total'])}\n"
            f"المستخدم: {format_bytes(snapshot['used'])}\n"
            f"المتاح: {format_bytes(snapshot['free'])}\n\n"
            "حذف الفيديوهات القديمة يحذف كل الفيديوهات المخزنة، وليس فقط غير المستخدمة.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🗑 حذف الفيديوهات القديمة", callback_data="settings:cleanup_confirm"
                        )
                    ],
                    [InlineKeyboardButton(
                        text="⬅️ رجوع", callback_data="settings:view"
                    )],
                ]
            ),
        )
        await query.answer()

    @router.callback_query(F.data == "settings:cleanup_confirm")
    async def cleanup(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        removed = await ctx.storage.remove_old_videos()
        await query.message.edit_text(f"✅ تم حذف {removed} فيديو.", reply_markup=back_keyboard())
        await query.answer()

    @router.callback_query(F.data.startswith("settings:edit:"))
    async def edit_setting(query: CallbackQuery, state: FSMContext) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        field = query.data.split(":", 2)[2]
        await state.update_data(setting_field=field)
        await state.set_state(SettingsStates.waiting_value)
        labels = {
            "channel_id": "Channel ID",
            "rtmp_url": "RTMP URL",
            "stream_key": "Stream Key",
            "video_bitrate": "Video Bitrate",
            "audio_bitrate": "Audio Bitrate",
            "resolution": "Resolution مثل 1280x720",
            "fps": "FPS",
        }
        await query.message.edit_text(
            f"أرسل قيمة {labels.get(field, field)}.",
            reply_markup=back_keyboard(),
        )
        await query.answer()

    @router.message(SettingsStates.waiting_value)
    async def save_setting(message: Message, state: FSMContext) -> None:
        if not owner_from_message(message, ctx):
            await deny_message(message)
            return
        data = await state.get_data()
        field = str(data.get("setting_field", ""))
        value = (message.text or "").strip()
        try:
            if field == "fps":
                value = int(value)
                if not 1 <= value <= 120:
                    raise ValueError
            if field == "resolution" and ("x" not in value.lower() or any(
                not part.isdigit() for part in value.lower().split("x", 1)
            )):
                raise ValueError
            if field not in {
                "channel_id",
                "rtmp_url",
                "stream_key",
                "video_bitrate",
                "audio_bitrate",
                "resolution",
                "fps",
            }:
                raise ValueError
            await ctx.database.update_settings({field: value})
            await state.clear()
            await message.answer("✅ تم حفظ الإعدادات.")
            await render(message)
        except ValueError:
            await message.answer("❌ القيمة غير صالحة. حاول مرة أخرى.")

    return router