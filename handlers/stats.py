from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app_context import AppContext
from handlers.common import deny_callback, owner_from_callback
from keyboards.main import back_keyboard


def get_router(ctx: AppContext) -> Router:
    router = Router(name="stats")

    @router.callback_query(F.data == "stats:view")
    async def stats(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        values = await ctx.monitor.stats()
        text = (
            "📊 STREAM STATUS\n\n"
            f"🟢 الحالة: {values['status']}\n"
            f"🎬 الفيديو: {values['video']}\n"
            f"⏱ مدة التشغيل: {values['uptime']}\n"
            f"🔄 مرات الاستعادة: {values['restarts']}\n"
            f"💾 التخزين: {values['storage']}\n"
            f"🧠 RAM: {values['ram']}\n"
            f"⚙️ CPU: {values['cpu']}\n"
            f"📡 العملية: {values['process']}\n"
            f"🕐 بدأ في: {values['started_at']}"
        )
        await query.message.edit_text(text, reply_markup=back_keyboard())
        await query.answer()

    return router