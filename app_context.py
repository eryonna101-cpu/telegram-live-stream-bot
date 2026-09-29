from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot

from config import Config
from database import Database
from services.controller import StreamController
from services.monitor import SystemMonitor
from services.storage import StorageService
from services.telegram_stream import TelegramStreamService


@dataclass(slots=True)
class AppContext:
    bot: Bot
    config: Config
    database: Database
    storage: StorageService
    telegram: TelegramStreamService
    controller: StreamController
    monitor: SystemMonitor