from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app_context import AppContext
from handlers.common import deny_callback, owner_from_callback
from keyboards.main import back_keyboard
from keyboards.videos import delete_confirm_keyboard, video_detail_keyboard, videos_keyboard
from utils.helpers import format_bytes, format_datetime, format_duration


PAGE_SIZE = 8


def get_router(ctx: AppContext) -> Router:
    router = Router(name="videos")

    @router.callback_query(F.data.startswith("videos:list:"))
    async def list_videos(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        page = max(0, int(query.data.rsplit(":", 1)[-1]))
        items = await ctx.database.list_videos(skip=page * PAGE_SIZE, limit=PAGE_SIZE + 1)
        has_next = len(items) > PAGE_SIZE
        items = items[:PAGE_SIZE]
        text = "📁 الفيديوهات\n\n"
        text += (
            "لا توجد فيديوهات بعد."
            if not items
            else f"عدد الفيديوهات المعروضة: {len(items)}\nاختر فيديو لعرض تفاصيله."
        )
        await query.message.edit_text(text, reply_markup=videos_keyboard(items, page, has_next))
        await query.answer()

    @router.callback_query(F.data.startswith("video:view:"))
    async def view_video(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        video_id = query.data.split(":", 2)[2]
        video = await ctx.database.get_video(video_id)
        if not video:
            await query.answer("الفيديو غير موجود", show_alert=True)
            return
        text = (
            f"🎬 {video['filename']}\n\n"
            f"الحجم: {format_bytes(video.get('size'))}\n"
            f"المدة: {format_duration(video.get('duration'))}\n"
            f"الصيغة: {video.get('format', 'غير معروفة')}\n"
            f"تاريخ الرفع: {format_datetime(video.get('created_at'))}"
        )
        await query.message.edit_text(text, reply_markup=video_detail_keyboard(video_id))
        await query.answer()

    @router.callback_query(F.data.startswith("video:delete:"))
    async def confirm_delete(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        video_id = query.data.split(":", 2)[2]
        await query.message.edit_text(
            "⚠️ هل تريد حذف هذا الفيديو من التخزين وقاعدة البيانات؟",
            reply_markup=delete_confirm_keyboard(video_id),
        )
        await query.answer()

    @router.callback_query(F.data.startswith("video:delete_yes:"))
    async def delete_video(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        video_id = query.data.split(":", 2)[2]
        status = await ctx.database.get_stream_status()
        if status.get("current_video_id") == video_id and status.get("should_run"):
            await query.answer("لا يمكن حذف فيديو قيد البث. أوقف البث أولاً.", show_alert=True)
            return
        video = await ctx.database.get_video(video_id)
        if not video:
            await query.answer("الفيديو غير موجود", show_alert=True)
            return
        await ctx.storage.delete_file(str(video["filepath"]))
        await ctx.database.delete_video(video_id)
        await query.message.edit_text("✅ تم حذف الفيديو.", reply_markup=back_keyboard())
        await query.answer()

    @router.callback_query(F.data.startswith("video:play:"))
    async def play_video(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        video_id = query.data.split(":", 2)[2]
        if not await ctx.database.get_video(video_id):
            await query.answer("الفيديو غير موجود", show_alert=True)
            return
        await ctx.controller.start(video_id=video_id, mode="LOOP")
        await query.message.edit_text(
            "▶️ جارٍ تشغيل الفيديو كبث مباشر في وضع Loop.",
            reply_markup=back_keyboard(),
        )
        await query.answer("تم تشغيل البث")

    return router