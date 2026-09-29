from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app_context import AppContext
from handlers.common import deny_callback, deny_message, owner_from_callback, owner_from_message
from keyboards.main import back_keyboard
from keyboards.videos import video_detail_keyboard
from utils.helpers import format_bytes, format_duration


class UploadStates(StatesGroup):
    waiting_video = State()


def get_router(ctx: AppContext) -> Router:
    router = Router(name="upload")

    @router.callback_query(F.data == "upload:start")
    async def request_video(query: CallbackQuery, state: FSMContext) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        await state.set_state(UploadStates.waiting_video)
        await query.message.edit_text(
            "📤 أرسل الفيديو الآن\n\n"
            "الصيغ المدعومة: MP4, MKV, MOV, AVI, WebM\n"
            "سيتم حفظه على القرص باسم آمن ولن يتم تحميله بالكامل إلى الذاكرة.",
            reply_markup=back_keyboard(),
        )
        await query.answer()

    @router.message(UploadStates.waiting_video, F.video)
    async def receive_video(message: Message, state: FSMContext) -> None:
        if not owner_from_message(message, ctx):
            await deny_message(message)
            return
        video = message.video
        if not video:
            await message.answer("❌ لم أجد فيديو في الرسالة.")
            return
        await message.answer("⏳ جارٍ تنزيل الفيديو وفحصه، قد يستغرق ذلك وقتاً للفيديوهات الكبيرة.")
        extension = ".mp4"
        original_name = video.file_name or f"telegram_{video.file_id}.mp4"
        if "." in original_name:
            extension = "." + original_name.rsplit(".", 1)[-1].lower()
        try:
            path, metadata = await ctx.storage.download_video(
                video.file_id, original_name, extension
            )
            stored = await ctx.database.add_video(
                {
                    "telegram_file_id": video.file_id,
                    "filename": original_name,
                    "filepath": str(path),
                    "size": metadata["size"],
                    "duration": metadata["duration"],
                    "format": metadata["format"],
                }
            )
            await state.clear()
            await message.answer(
                "🎬 تم رفع الفيديو بنجاح\n\n"
                f"الاسم: {stored['filename']}\n"
                f"الحجم: {format_bytes(stored['size'])}\n"
                f"المدة: {format_duration(stored['duration'])}\n"
                f"الصيغة: {stored['format']}",
                reply_markup=video_detail_keyboard(stored["id"]),
            )
        except Exception as exc:
            await message.answer(f"❌ فشل تحميل الفيديو: {exc}", reply_markup=back_keyboard())

    @router.message(UploadStates.waiting_video)
    async def reject_non_video(message: Message) -> None:
        if owner_from_message(message, ctx):
            await message.answer("أرسل ملف فيديو فقط أو اضغط رجوع.")
        else:
            await deny_message(message)

    return router