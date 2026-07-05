from __future__ import annotations

from pydantic import BaseModel, Field

from .models import ActivityLevel, Gender, HealthGoal


class OnboardingProfile(BaseModel):
    telegram_user_id: int
    chat_id: int
    name: str
    goal: HealthGoal
    gender: Gender
    age: int = Field(ge=10, le=100)
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    activity_level: ActivityLevel


class MealAnalysis(BaseModel):
    item_name: str
    calories: float
    protein_g: float
    carbs_g: float
    fats_g: float
    portion_description: str
    confidence: float = Field(ge=0, le=1)
    warning: str = ""
    balance_tip: str = ""


class MacroTargets(BaseModel):
    calories: int
    protein_g: int
    carbs_g: int
    fats_g: int


class WaterEntryDTO(BaseModel):
    telegram_user_id: int
    glasses: float


class ExerciseEntryDTO(BaseModel):
    telegram_user_id: int
    description: str
    minutes: int


class DailySummary(BaseModel):
    title: str
    calories_target: int
    calories_consumed: int
    protein_target_g: int
    protein_consumed_g: float
    carbs_target_g: int
    carbs_consumed_g: float
    fats_target_g: int
    fats_consumed_g: float
    meals: list[str]
    status: str
