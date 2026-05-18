from __future__ import annotations

from .chat_graph import LangGraphChatService
from .config import get_settings
from .db import Database
from .service import MealTrackingService
from .scheduler import register_daily_report_job
from .telegram_bot import build_application


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
