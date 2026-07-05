from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from meal_tracking_agent.chat_graph import LangGraphChatService
from meal_tracking_agent.config import get_settings
from meal_tracking_agent.db import Database
from meal_tracking_agent.service import MealTrackingService
from meal_tracking_agent.scheduler import register_daily_report_job
from meal_tracking_agent.telegram_bot import build_application


def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and set it first.")

    database = Database(settings.database_url)
    database.init_db()
    service = MealTrackingService(settings, database)
    chat_service = LangGraphChatService(settings, service)
    application = build_application(settings, database, service, chat_service)
    register_daily_report_job(application, settings)
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
