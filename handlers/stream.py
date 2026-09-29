from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app_context import AppContext
from handlers.common import deny_callback, owner_from_callback, show_home_callback
from keyboards.main import back_keyboard


async def _source_for_start(ctx: AppContext) -> tuple[str | None, str | None, str] | None:
    playlist = await ctx.database.get_active_playlist()
    if playlist and playlist.get("video_ids"):
        return None, playlist["id"], "PLAYLIST"
    videos = await ctx.database.list_videos(limit=2)
    if len(videos) == 1:
        return videos[0]["id"], None, "LOOP"
    return None


def get_router(ctx: AppContext) -> Router:
    router = Router(name="stream")

    @router.callback_query(F.data == "stream:start")
    async def start_stream(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        source = await _source_for_start(ctx)
        if not source:
            await query.message.edit_text(
                "▶️ اختر فيديو من قائمة الفيديوهات لتشغيله، أو أنشئ Playlist.",
                reply_markup=back_keyboard(),
            )
            await query.answer()
            return
        video_id, playlist_id, mode = source
        await ctx.controller.start(video_id=video_id, playlist_id=playlist_id, mode=mode)
        await query.message.edit_text("▶️ جارٍ بدء البث...", reply_markup=back_keyboard())
        await query.answer("جارٍ تشغيل البث")

    @router.callback_query(F.data == "stream:playlist")
    async def start_playlist(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        playlist = await ctx.database.get_active_playlist()
        if not playlist or not playlist.get("video_ids"):
            await query.answer("الـPlaylist فارغة", show_alert=True)
            return
        await ctx.controller.start(playlist_id=playlist["id"], mode="PLAYLIST")
        await query.message.edit_text("▶️ جارٍ تشغيل الـPlaylist...", reply_markup=back_keyboard())
        await query.answer()

    @router.callback_query(F.data == "stream:pause")
    async def pause_stream(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        await ctx.controller.stop("إيقاف مؤقت من المالك")
        await query.message.edit_text("⏸ تم إيقاف البث مؤقتاً.", reply_markup=back_keyboard())
        await query.answer()

    @router.callback_query(F.data == "stream:stop")
    async def stop_stream(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        await ctx.controller.stop("إيقاف من المالك")
        await show_home_callback(query, ctx)

    @router.callback_query(F.data == "stream:restart")
    async def restart_stream(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        status = await ctx.database.get_stream_status()
        video_id = status.get("current_video_id")
        playlist_id = status.get("current_playlist_id")
        mode = status.get("mode", "LOOP")
        if not video_id and not playlist_id:
            source = await _source_for_start(ctx)
            if not source:
                await query.answer("لا يوجد فيديو لتشغيله", show_alert=True)
                return
            video_id, playlist_id, mode = source
        await ctx.controller.restart(video_id=video_id, playlist_id=playlist_id, mode=mode)
        await query.message.edit_text("🔄 جارٍ إعادة تشغيل البث...", reply_markup=back_keyboard())
        await query.answer()

    return router