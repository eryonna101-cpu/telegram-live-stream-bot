from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app_context import AppContext
from handlers.common import deny_callback, owner_from_callback, show_home_callback


def get_router(ctx: AppContext) -> Router:
    router = Router(name="menu")

    @router.callback_query(F.data.in_({"menu:home", "menu:refresh"}))
    async def home(query: CallbackQuery) -> None:
        if not owner_from_callback(query, ctx):
            await deny_callback(query)
            return
        await show_home_callback(query, ctx)

    return router