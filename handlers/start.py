from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app_context import AppContext
from handlers.common import deny_message, owner_from_message, show_home_message


def get_router(ctx: AppContext) -> Router:
    router = Router(name="start")

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        if not owner_from_message(message, ctx):
            await deny_message(message)
            return
        if message.from_user:
            await ctx.database.upsert_user(
                message.from_user.id, message.from_user.username
            )
        await show_home_message(message, ctx)

    return router