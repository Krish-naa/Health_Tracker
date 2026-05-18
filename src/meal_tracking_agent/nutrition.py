from __future__ import annotations

from .models import ActivityLevel, Gender, HealthGoal
from .schemas import MacroTargets, OnboardingProfile


_ACTIVITY_MULTIPLIER = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.lightly_active: 1.375,
    ActivityLevel.active: 1.55,
    ActivityLevel.very_active: 1.725,
}


def calculate_targets(profile: OnboardingProfile) -> MacroTargets:
    if profile.gender == Gender.male:
        bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
    elif profile.gender == Gender.female:
        bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161
    else:
        bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 78

    maintenance_calories = bmr * _ACTIVITY_MULTIPLIER[profile.activity_level]
    if profile.goal == HealthGoal.lose_weight:
        calorie_target = int(round(maintenance_calories - 400))
        protein_per_kg = 1.8
        fat_ratio = 0.28
    elif profile.goal == HealthGoal.gain_muscle:
        calorie_target = int(round(maintenance_calories + 250))
        protein_per_kg = 2.0
        fat_ratio = 0.26
    elif profile.goal == HealthGoal.eat_healthy:
        calorie_target = int(round(maintenance_calories))
        protein_per_kg = 1.6
        fat_ratio = 0.30
    else:
        calorie_target = int(round(maintenance_calories))
        protein_per_kg = 1.6
        fat_ratio = 0.30

    protein_g = max(80, int(round(profile.weight_kg * protein_per_kg)))
    fats_g = max(40, int(round((calorie_target * fat_ratio) / 9)))
    carbs_g = max(80, int(round((calorie_target - (protein_g * 4) - (fats_g * 9)) / 4)))

    return MacroTargets(
        calories=calorie_target,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fats_g=fats_g,
    )


def sample_meal_plan(goal: HealthGoal) -> list[str]:
    if goal == HealthGoal.lose_weight:
        return [
            "Breakfast: Greek yogurt, berries, and oats",
            "Lunch: Grilled chicken salad with quinoa",
            "Dinner: Paneer or tofu bowl with vegetables",
        ]
    if goal == HealthGoal.gain_muscle:
        return [
            "Breakfast: Eggs, toast, and fruit",
            "Lunch: Rice, lentils, chicken, and vegetables",
            "Dinner: Salmon or paneer with potatoes and salad",
        ]
    if goal == HealthGoal.eat_healthy:
        return [
            "Breakfast: Fruit, yogurt, and seeds",
            "Lunch: Balanced grain bowl with protein",
            "Dinner: Mixed vegetables, lentils, and roti",
        ]
    return [
        "Breakfast: Oats with fruit and nuts",
        "Lunch: Rice, dal, and mixed vegetables",
        "Dinner: Protein-rich main dish with salad",
    ]
