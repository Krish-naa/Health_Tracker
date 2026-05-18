from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from .anthropic_client import ClaudeMealAnalyzer, MealImageInput
from .config import Settings
from .db import (
    add_meal_entry,
    get_profile,
    list_profiles,
    meal_totals_for_date,
    meals_for_date,
    meals_for_month,
    upsert_profile,
)
from .models import ActivityLevel, Gender, HealthGoal
from .nutrition import calculate_targets, sample_meal_plan
from .schemas import DailySummary, MealAnalysis, OnboardingProfile


class MealTrackingService:
    def __init__(self, settings: Settings, database: object) -> None:
        self.settings = settings
        self.database = database
        self.analyzer = ClaudeMealAnalyzer(settings)

    def save_profile(self, session: Session, profile: OnboardingProfile) -> tuple[object, list[str]]:
        targets = calculate_targets(profile)
        record = upsert_profile(session, profile, targets)
        return record, sample_meal_plan(profile.goal)

    def get_profile(self, session: Session, telegram_user_id: int):
        return get_profile(session, telegram_user_id)

    def analyze_and_log_meal(
        self,
        session: Session,
        telegram_user_id: int,
        profile: Optional[OnboardingProfile],
        image_bytes: bytes,
        mime_type: str,
        file_id: Optional[str],
    ) -> tuple[MealAnalysis, object]:
        analysis = self.analyzer.analyze(MealImageInput(image_bytes=image_bytes, mime_type=mime_type), profile)
        entry = add_meal_entry(session, telegram_user_id, analysis, file_id)
        return analysis, entry

    def build_daily_summary(self, session: Session, telegram_user_id: int, target_date: Optional[date] = None) -> DailySummary:
        target_date = target_date or datetime.now(ZoneInfo(self.settings.timezone)).date()
        profile = get_profile(session, telegram_user_id)
        totals = meal_totals_for_date(session, telegram_user_id, target_date)
        meals = meals_for_date(session, telegram_user_id, target_date)
        if profile is None:
            return DailySummary(
                title="No profile yet",
                calories_target=0,
                calories_consumed=int(totals["calories"]),
                protein_target_g=0,
                protein_consumed_g=totals["protein_g"],
                carbs_target_g=0,
                carbs_consumed_g=totals["carbs_g"],
                fats_target_g=0,
                fats_consumed_g=totals["fats_g"],
                meals=[f"{meal.meal_name} — {meal.calories:.0f} kcal" for meal in meals],
                status="Create your profile with /start to unlock targets.",
            )

        meals_text = [
            f"{meal.eaten_at.strftime('%H:%M')} — {meal.meal_name}: {meal.calories:.0f} kcal, "
            f"P {meal.protein_g:.0f}g, C {meal.carbs_g:.0f}g, F {meal.fats_g:.0f}g"
            for meal in meals
        ]
        status = self._status_text(totals["calories"], profile.calorie_target)
        return DailySummary(
            title=f"{profile.name}'s day summary",
            calories_target=profile.calorie_target,
            calories_consumed=int(round(totals["calories"])),
            protein_target_g=profile.protein_target_g,
            protein_consumed_g=round(totals["protein_g"], 1),
            carbs_target_g=profile.carbs_target_g,
            carbs_consumed_g=round(totals["carbs_g"], 1),
            fats_target_g=profile.fats_target_g,
            fats_consumed_g=round(totals["fats_g"], 1),
            meals=meals_text,
            status=status,
        )

    def build_monthly_summary(self, session: Session, telegram_user_id: int) -> str:
        profile = get_profile(session, telegram_user_id)
        now = datetime.now(ZoneInfo(self.settings.timezone))
        month_meals = meals_for_month(session, telegram_user_id, now)
        if not month_meals:
            return "No meals logged yet this month."

        daily_totals: dict[date, float] = {}
        for meal in month_meals:
            meal_day = meal.eaten_at.date()
            daily_totals.setdefault(meal_day, 0.0)
            daily_totals[meal_day] += meal.calories

        average_daily = sum(daily_totals.values()) / len(daily_totals)
        if profile is None:
            return f"Monthly average calories: {average_daily:.0f} kcal/day across {len(daily_totals)} logged days."

        on_track_days = sum(1 for total in daily_totals.values() if abs(total - profile.calorie_target) <= profile.calorie_target * 0.15)
        off_track_days = len(daily_totals) - on_track_days
        return (
            f"Monthly summary for {profile.name}:\n"
            f"Average daily calories: {average_daily:.0f} kcal\n"
            f"On-track days: {on_track_days}\n"
            f"Off-track days: {off_track_days}\n"
            f"Current target: {profile.calorie_target} kcal\n"
            f"Suggestion: aim for consistent protein intake and keep snacks planned."
        )

    def build_daily_report_text(self, session: Session, telegram_user_id: int) -> str:
        summary = self.build_daily_summary(session, telegram_user_id)
        lines = [summary.title, ""]
        lines.extend(summary.meals or ["No meals logged today."])
        lines.append("")
        lines.append(
            f"Calories: {summary.calories_consumed}/{summary.calories_target} | "
            f"Protein: {summary.protein_consumed_g}/{summary.protein_target_g} g | "
            f"Carbs: {summary.carbs_consumed_g}/{summary.carbs_target_g} g | "
            f"Fats: {summary.fats_consumed_g}/{summary.fats_target_g} g"
        )
        lines.append(summary.status)
        lines.append("Tip: keep tomorrow’s first meal protein-forward to stay on track.")
        return "\n".join(lines)

    def _status_text(self, consumed: float, target: int) -> str:
        if target <= 0:
            return "No target available."
        if consumed < target * 0.9:
            return "You are under target today."
        if consumed > target * 1.1:
            return "You are over target today."
        return "You are on track today."
