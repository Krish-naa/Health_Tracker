from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

from .models import HealthGoal
from .config import Settings
from .schemas import MealAnalysis, OnboardingProfile


@dataclass(slots=True)
class MealImageInput:
    image_bytes: bytes
    mime_type: str
    file_name: Optional[str] = None


class ClaudeMealAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    def analyze(self, image: MealImageInput, profile: Optional[OnboardingProfile] = None) -> MealAnalysis:
        if self.client is None:
            return self._fallback_analysis(profile)

        prompt = self._build_prompt(profile)
        message = self.client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=900,
            temperature=0.2,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image.mime_type,
                                "data": base64.b64encode(image.image_bytes).decode("utf-8"),
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
        return self._parse_analysis(text, profile)

    def _build_prompt(self, profile: Optional[OnboardingProfile]) -> str:
        base = (
            "Analyze this meal photo for a Telegram meal tracker. Return only valid JSON with keys: "
            "item_name, calories, protein_g, carbs_g, fats_g, portion_description, confidence, warning, balance_tip. "
            "Be practical and estimate portion sizes from a normal serving."
        )
        if profile is None:
            return base
        return (
            base
            + f" The user goal is {profile.goal.value}, age {profile.age}, gender {profile.gender.value}, "
            f"weight {profile.weight_kg} kg, height {profile.height_cm} cm, activity {profile.activity_level.value}. "
            "Tune warnings and tips to that goal."
        )

    def _parse_analysis(self, text: str, profile: Optional[OnboardingProfile]) -> MealAnalysis:
        try:
            data = json.loads(text)
            return MealAnalysis.model_validate(data)
        except Exception:
            return self._fallback_analysis(profile)

    def _fallback_analysis(self, profile: Optional[OnboardingProfile]) -> MealAnalysis:
        warning = None
        tip = None
        if profile and profile.goal == HealthGoal.lose_weight:
            warning = "This looks like a calorie-dense meal."
            tip = "Balance it with a protein side and a salad."
        return MealAnalysis(
            item_name="Mixed meal",
            calories=520,
            protein_g=24,
            carbs_g=58,
            fats_g=18,
            portion_description="Estimated one medium plate",
            confidence=0.45,
            warning=warning,
            balance_tip=tip or "Add vegetables or a protein source to improve balance.",
        )
