from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from meal_tracking_agent.telegram_bot import _reply_text as reply_text
from meal_tracking_agent.db import Database
from meal_tracking_agent.models import MealEntry
from meal_tracking_agent.schemas import MealAnalysis
from meal_tracking_agent.service import MealTrackingService


class DummyMessage:
    def __init__(self):
        self.sent = []

    async def reply_text(self, text, **kwargs):
        self.sent.append((text, kwargs))


class DummyCallbackQuery:
    def __init__(self, message):
        self.message = message


class DummyUpdate:
    def __init__(self, message=None, callback_query=None):
        self.message = message
        self.callback_query = callback_query


def test_callback_query_messages_are_replied_via_the_callback_message(tmp_path):
    message = DummyMessage()
    update = DummyUpdate(callback_query=DummyCallbackQuery(message))

    async def run_test():
        await reply_text(update, "hello")

    import asyncio

    asyncio.run(run_test())

    assert message.sent == [("hello", {})]


def test_init_db_creates_expected_meal_entry_columns(tmp_path):
    db_path = tmp_path / "legacy.db"
    db = Database(f"sqlite:///{db_path}")
    db.init_db()

    migrated_conn = sqlite3.connect(db_path)
    try:
        columns = [row[1] for row in migrated_conn.execute("PRAGMA table_info(meal_entries)")]
        assert "edited_at" in columns
        assert "raw_analysis_json" in columns
        assert "image_file_id" in columns
    finally:
        migrated_conn.close()


def test_meal_update_and_delete_round_trip(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'test.db'}")
    db.init_db()

    session = db.session()
    entry = MealEntry(
        telegram_user_id=1,
        meal_name="Breakfast",
        calories=400,
        protein_g=20,
        carbs_g=50,
        fats_g=10,
        notes="old",
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)

    entry.meal_name = "Lunch"
    entry.calories = 450
    entry.notes = "updated"
    session.commit()

    updated = session.get(MealEntry, entry.id)
    assert updated is not None
    assert updated.meal_name == "Lunch"
    assert updated.calories == 450
    assert updated.notes == "updated"

    session.delete(updated)
    session.commit()

    assert session.get(MealEntry, entry.id) is None
