from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, ExerciseEntry, MealEntry, UserProfile, WaterEntry
from .schemas import MealAnalysis, MacroTargets, OnboardingProfile


class Database:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, connect_args=connect_args, future=True)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def init_db(self) -> None:
        if self.engine.url.drivername.startswith("sqlite"):
            db_path = self.engine.url.database
            if db_path and db_path not in {":memory:"}:
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self.session_factory()


def upsert_profile(session: Session, profile: OnboardingProfile, targets: MacroTargets) -> UserProfile:
    existing = session.scalar(select(UserProfile).where(UserProfile.telegram_user_id == profile.telegram_user_id))
    if existing is None:
        existing = UserProfile(telegram_user_id=profile.telegram_user_id, chat_id=profile.chat_id)
        session.add(existing)

    existing.name = profile.name
    existing.goal = profile.goal.value
    existing.gender = profile.gender.value
    existing.age = profile.age
    existing.height_cm = profile.height_cm
    existing.weight_kg = profile.weight_kg
    existing.activity_level = profile.activity_level.value
    existing.calorie_target = targets.calories
    existing.protein_target_g = targets.protein_g
    existing.carbs_target_g = targets.carbs_g
    existing.fats_target_g = targets.fats_g
    session.commit()
    session.refresh(existing)
    return existing


def get_profile(session: Session, telegram_user_id: int) -> Optional[UserProfile]:
    return session.scalar(select(UserProfile).where(UserProfile.telegram_user_id == telegram_user_id))


def list_profiles(session: Session) -> list[UserProfile]:
    return list(session.scalars(select(UserProfile).order_by(UserProfile.created_at.asc())).all())


def add_meal_entry(
    session: Session,
    telegram_user_id: int,
    meal_analysis: MealAnalysis,
    image_file_id: Optional[str] = None,
) -> MealEntry:
    entry = MealEntry(
        telegram_user_id=telegram_user_id,
        meal_name=meal_analysis.item_name,
        calories=meal_analysis.calories,
        protein_g=meal_analysis.protein_g,
        carbs_g=meal_analysis.carbs_g,
        fats_g=meal_analysis.fats_g,
        notes=meal_analysis.warning or meal_analysis.balance_tip,
        image_file_id=image_file_id,
        raw_analysis_json=meal_analysis.model_dump_json(),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def meal_totals_for_date(session: Session, telegram_user_id: int, target_date: date) -> dict[str, float]:
    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)
    row = session.execute(
        select(
            func.coalesce(func.sum(MealEntry.calories), 0),
            func.coalesce(func.sum(MealEntry.protein_g), 0),
            func.coalesce(func.sum(MealEntry.carbs_g), 0),
            func.coalesce(func.sum(MealEntry.fats_g), 0),
        ).where(
            MealEntry.telegram_user_id == telegram_user_id,
            MealEntry.eaten_at >= start,
            MealEntry.eaten_at < end,
        )
    ).one()
    calories, protein, carbs, fats = row
    return {
        "calories": float(calories or 0),
        "protein_g": float(protein or 0),
        "carbs_g": float(carbs or 0),
        "fats_g": float(fats or 0),
    }


def meals_for_date(session: Session, telegram_user_id: int, target_date: date) -> list[MealEntry]:
    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)
    return list(
        session.scalars(
            select(MealEntry)
            .where(
                MealEntry.telegram_user_id == telegram_user_id,
                MealEntry.eaten_at >= start,
                MealEntry.eaten_at < end,
            )
            .order_by(MealEntry.eaten_at.asc())
        ).all()
    )


def meals_for_month(session: Session, telegram_user_id: int, anchor: datetime) -> list[MealEntry]:
    start = anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return list(
        session.scalars(
            select(MealEntry)
            .where(
                MealEntry.telegram_user_id == telegram_user_id,
                MealEntry.eaten_at >= start,
                MealEntry.eaten_at < end,
            )
            .order_by(MealEntry.eaten_at.asc())
        ).all()
    )


def get_meal_entry(session: Session, entry_id: int) -> Optional[MealEntry]:
    return session.get(MealEntry, entry_id)


def update_meal_entry(session: Session, entry_id: int, **fields: object) -> Optional[MealEntry]:
    entry = session.get(MealEntry, entry_id)
    if entry is None:
        return None
    for field, value in fields.items():
        if value is None:
            continue
        setattr(entry, field, value)
    entry.edited_at = datetime.utcnow()
    session.commit()
    session.refresh(entry)
    return entry


def delete_meal_entry(session: Session, entry_id: int) -> bool:
    entry = session.get(MealEntry, entry_id)
    if entry is None:
        return False
    session.delete(entry)
    session.commit()
    return True


def meals_recent(session: Session, telegram_user_id: int, limit: int = 6) -> list[MealEntry]:
    return list(
        session.scalars(
            select(MealEntry)
            .where(MealEntry.telegram_user_id == telegram_user_id)
            .order_by(MealEntry.eaten_at.desc())
            .limit(limit)
        ).all()
    )


def add_water_entry(session: Session, telegram_user_id: int, glasses: float) -> WaterEntry:
    entry = WaterEntry(telegram_user_id=telegram_user_id, glasses=glasses)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def add_exercise_entry(session: Session, telegram_user_id: int, description: str, minutes: int) -> ExerciseEntry:
    entry = ExerciseEntry(telegram_user_id=telegram_user_id, description=description, minutes=minutes)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry
