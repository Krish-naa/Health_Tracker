from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    database_url: str = Field(default="sqlite:///./meal_tracking.db", alias="DATABASE_URL")
    timezone: str = Field(default="Asia/Kolkata", alias="TIMEZONE")
    daily_report_hour: int = Field(default=23, alias="DAILY_REPORT_HOUR")
    daily_report_minute: int = Field(default=0, alias="DAILY_REPORT_MINUTE")
    webhook_url: str = Field(default="", alias="WEBHOOK_URL")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")
    bot_mode: str = Field(default="polling", alias="BOT_MODE")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", alias="ANTHROPIC_MODEL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    llm_provider: str = Field(default="auto", alias="LLM_PROVIDER")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
