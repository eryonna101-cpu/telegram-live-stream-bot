from __future__ import annotations

import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app_context import AppContext
from config import Config, load_config
from database import Database
from handlers import menu, playlists, settings, start, stats, stream, upload, videos
from services.controller import StreamController
from services.ffmpeg import FFmpegService
from services.monitor import SystemMonitor
from services.storage import StorageService
from services.telegram_stream import TelegramStreamService
from utils.logger import configure_logging


async def run() -> None:
    config = load_config()
    logger = configure_logging(config.log_dir)
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    database = Database(config.mongo_uri, config.mongo_database, logger)
    await database.connect()

    initial_settings = await database.get_settings()
    settings_update = {
        "channel_id": initial_settings.get("channel_id") or config.channel_id,
        "rtmp_url": initial_settings.get("rtmp_url") or config.rtmp_url,
        "stream_key": initial_settings.get("stream_key") or config.stream_key,
        "video_bitrate": initial_settings.get("video_bitrate") or config.video_bitrate,
        "audio_bitrate": initial_settings.get("audio_bitrate") or config.audio_bitrate,
        "resolution": initial_settings.get("resolution") or config.resolution,
        "fps": initial_settings.get("fps") or config.fps,
        "preset": initial_settings.get("preset") or config.ffmpeg_preset,
    }
    await database.update_settings(settings_update)

    async def notify_owner(text: str) -> None:
        try:
            await bot.send_message(config.owner_id, text)
        except Exception:
            logger.exception("Could not notify owner")

    storage = StorageService(bot, database, config.video_dir, logger)
    telegram = TelegramStreamService(
        config.api_id,
        config.api_hash,
        config.pyrogram_session_name,
        config.channel_id,
        logger,
    )
    controller = StreamController(
        database,
        FFmpegService(logger),
        logger,
        config.ffmpeg_restart_limit,
        config.ffmpeg_restart_delay,
        notify_owner,
    )
    monitor = SystemMonitor(
        database, storage, logger, config.low_storage_gb, notify_owner
    )
    context = AppContext(
        bot=bot,
        config=config,
        database=database,
        storage=storage,
        telegram=telegram,
        controller=controller,
        monitor=monitor,
    )

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(start.get_router(context))
    dispatcher.include_router(menu.get_router(context))
    dispatcher.include_router(upload.get_router(context))
    dispatcher.include_router(videos.get_router(context))
    dispatcher.include_router(playlists.get_router(context))
    dispatcher.include_router(stream.get_router(context))
    dispatcher.include_router(settings.get_router(context))
    dispatcher.include_router(stats.get_router(context))

    monitor.start()
    persisted = await database.get_stream_status()
    if persisted.get("should_run") and (
        persisted.get("current_video_id") or persisted.get("current_playlist_id")
    ):
        logger.info("Restoring the persisted stream after startup")
        await controller.start(
            video_id=persisted.get("current_video_id"),
            playlist_id=persisted.get("current_playlist_id"),
            mode=str(persisted.get("mode", "LOOP")),
        )

    stop_event = asyncio.Event()

    def request_stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(shutdown_signal, request_stop)
        except NotImplementedError:
            pass

    polling_task = asyncio.create_task(
        dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        ),
        name="telegram-polling",
    )
    try:
        await stop_event.wait()
    finally:
        polling_task.cancel()
        await asyncio.gather(polling_task, return_exceptions=True)
        await controller.stop("إغلاق الخدمة")
        await monitor.stop()
        await bot.session.close()
        await database.close()
        logger.info("Telegram live bot stopped")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.getLogger("telegram_live_bot").exception("Fatal startup error")
        raise


if __name__ == "__main__":
    main()