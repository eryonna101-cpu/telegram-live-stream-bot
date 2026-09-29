from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app_context import AppContext
from handlers.common import deny_callback, deny_message, owner_from_callback, owner_from_message
from keyboards.main import back_keyboard
from keyboards.playlists import playlist_item_keyboard, playlist_keyboard
from utils.helpers import format_duration


class PlaylistStates(StatesGroup):
    waiting_name = State()


async def render_playlist(ctx: AppContext) -> tuple[str, dict | None]:
    playlist = await ctx.database.get_active_playlist()
    if not playlist:
        return "📋 Playlist\n\nلا توجد Playlist. أنشئ واحدة للبدء.", None
    lines = [f"📋 Playlist: {playlist.get('name', 'الرئيسية')}", ""]
    ids = playlist.get("video_ids", [])
    if not ids:
        lines.append("لا توجد فيديوهات في هذه القائمة.")
    for index, video_id in enumerate(ids, 1):
        video = await ctx.database.get_video(video_id)
        lines.append(f"{index}. {video.get('filename', video_id) if video else 'فيديو محذوف'}")
    return "\n".join(lines), playlist


def get_router(ctx: AppContext) -> Router:
    router = Router(name="playlists")

    @router.callback_query(F.data == "playlist:view")
    async def view_playlist(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        text, playlist = await render_playlist(ctx)
        await query.message.edit_text(text, reply_markup=playlist_keyboard(playlist))
        if playlist:
            ids = playlist.get("video_ids", [])
            for index, video_id in enumerate(ids):
                video = await ctx.database.get_video(video_id)
                if video:
                    await query.message.answer(
                        f"{index + 1}. {video['filename']} ({format_duration(video.get('duration'))})",
                        reply_markup=playlist_item_keyboard(
                            playlist["id"], video_id, index, len(ids)
                        ),
                    )
        await query.answer()

    @router.callback_query(F.data == "playlist:new")
    async def new_playlist(query: CallbackQuery, state: FSMContext) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        await state.set_state(PlaylistStates.waiting_name)
        await query.message.edit_text(
            "🆕 أرسل اسم الـPlaylist الجديدة.", reply_markup=back_keyboard()
        )
        await query.answer()

    @router.message(PlaylistStates.waiting_name)
    async def create_playlist(message: Message, state: FSMContext) -> None:
        if not owner_from_message(message, ctx):
            await deny_message(message)
            return
        name = (message.text or "").strip()
        if not name or len(name) > 80:
            await message.answer("استخدم اسماً من 1 إلى 80 حرفاً.")
            return
        await ctx.database.create_playlist(name)
        await state.clear()
        text, playlist = await render_playlist(ctx)
        await message.answer(text, reply_markup=playlist_keyboard(playlist))

    @router.callback_query(F.data == "playlist:add_menu")
    async def add_menu(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        videos = await ctx.database.list_videos(limit=50)
        if not videos:
            await query.answer("ارفع فيديو أولاً", show_alert=True)
            return
        await query.message.edit_text(
            "➕ اختر فيديو لإضافته إلى الـPlaylist.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"🎬 {video.get('filename', 'فيديو')[:36]}",
                            callback_data=f"playlist:add:{video['id']}",
                        )
                    ]
                    for video in videos
                ]
                + [[InlineKeyboardButton(text="⬅️ رجوع", callback_data="playlist:view")]]
            ),
        )
        await query.answer()

    @router.callback_query(F.data.startswith("playlist:add:"))
    async def add_video(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        video_id = query.data.split(":", 2)[2]
        playlist = await ctx.database.get_active_playlist()
        if not playlist:
            playlist = await ctx.database.create_playlist("الرئيسية")
        changed = await ctx.database.add_video_to_playlist(playlist["id"], video_id)
        await query.answer("✅ تمت الإضافة" if changed else "الفيديو موجود بالفعل", show_alert=True)
        text, current = await render_playlist(ctx)
        await query.message.edit_text(text, reply_markup=playlist_keyboard(current))

    @router.callback_query(F.data.startswith("playlist:remove:"))
    async def remove_video(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        _, _, playlist_id, video_id = query.data.split(":", 3)
        await ctx.database.remove_video_from_playlist(playlist_id, video_id)
        await query.answer("تمت الإزالة")
        text, playlist = await render_playlist(ctx)
        await query.message.edit_text(text, reply_markup=playlist_keyboard(playlist))

    @router.callback_query(F.data.startswith("playlist:move:"))
    async def move_video(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        _, _, playlist_id, video_id, direction = query.data.split(":", 4)
        await ctx.database.move_playlist_item(playlist_id, video_id, int(direction))
        await query.answer("تم تحديث الترتيب")
        text, playlist = await render_playlist(ctx)
        await query.message.edit_text(text, reply_markup=playlist_keyboard(playlist))

    return router