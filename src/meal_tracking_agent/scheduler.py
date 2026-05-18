from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

from telegram.error import TelegramError
from telegram.ext import Application

from .config import Settings
from .db import list_profiles
from .service import MealTrackingService


async def send_daily_reports(context) -> None:
    application: Application = context.application
    service: MealTrackingService = application.bot_data["service"]
    database = application.bot_data["database"]

    with database.session() as session:
        profiles = list_profiles(session)
        for profile in profiles:
            try:
                report_text = service.build_daily_report_text(session, profile.telegram_user_id)
                await application.bot.send_message(chat_id=profile.chat_id, text=report_text)
            except TelegramError:
                continue


def register_daily_report_job(application: Application, settings: Settings) -> None:
    tz = ZoneInfo(settings.timezone)
    application.job_queue.run_daily(
        send_daily_reports,
        time=time(hour=settings.daily_report_hour, minute=settings.daily_report_minute, tzinfo=tz),
        name="daily_meal_report",
    )
