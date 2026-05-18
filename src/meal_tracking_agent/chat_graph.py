from __future__ import annotations

from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from .config import Settings
from .knowledge_base import search_knowledge
from .schemas import OnboardingProfile
from .service import MealTrackingService


class LangGraphChatService:
    def __init__(self, settings: Settings, meal_service: MealTrackingService) -> None:
        self.settings = settings
        self.meal_service = meal_service
        self.memory = MemorySaver()

    def reply(
        self,
        session,
        user_id: int,
        user_text: str,
        thread_id: str,
        profile: Optional[OnboardingProfile] = None,
    ) -> str:
        model = self._build_model()
        if model is None:
            return self._fallback_reply(user_text)

        agent = create_react_agent(
            model=model,
            tools=self._build_tools(session=session, user_id=user_id),
            prompt=self._system_prompt(profile),
            checkpointer=self.memory,
        )
        result = agent.invoke(
            {"messages": [HumanMessage(content=user_text)]},
            config={"configurable": {"thread_id": thread_id}},
        )
        messages = result.get("messages", [])
        if not messages:
            return "I'm here, but I couldn't generate a reply."
        return str(getattr(messages[-1], "content", "")).strip() or "I'm here, but I couldn't generate a reply."

    def _build_model(self):
        provider = self._choose_provider()
        if provider == "openai":
            return ChatOpenAI(model=self.settings.openai_model, api_key=self.settings.openai_api_key, temperature=0.4)
        if provider == "anthropic":
            return ChatAnthropic(model=self.settings.anthropic_model, api_key=self.settings.anthropic_api_key, temperature=0.4)
        if self.settings.openai_api_key:
            return ChatOpenAI(model=self.settings.openai_model, api_key=self.settings.openai_api_key, temperature=0.4)
        if self.settings.anthropic_api_key:
            return ChatAnthropic(model=self.settings.anthropic_model, api_key=self.settings.anthropic_api_key, temperature=0.4)
        return None

    def _build_tools(self, session, user_id: int):
        meal_service = self.meal_service

        @tool("today_summary")
        def today_summary() -> str:
            """Get the user's meal summary for today."""
            return meal_service.build_daily_report_text(session, user_id)

        @tool("month_summary")
        def month_summary() -> str:
            """Get the user's monthly meal summary."""
            return meal_service.build_monthly_summary(session, user_id)

        @tool("nutrition_guidance_search")
        def nutrition_guidance_search(query: str) -> str:
            """Retrieve concise nutrition guidance from the local knowledge base."""
            return search_knowledge(query)

        return [today_summary, month_summary, nutrition_guidance_search]

    def _choose_provider(self) -> str:
        if self.settings.llm_provider in {"anthropic", "openai"}:
            return self.settings.llm_provider
        if self.settings.openai_api_key:
            return "openai"
        if self.settings.anthropic_api_key:
            return "anthropic"
        return "fallback"

    def _system_prompt(self, profile: Optional[OnboardingProfile] = None) -> str:
        profile_context = ""
        if profile is not None:
            profile_context = (
                f" The current user is {profile.name}, goal {profile.goal.value}, gender {profile.gender.value}, "
                f"age {profile.age}, height {profile.height_cm} cm, weight {profile.weight_kg} kg, "
                f"activity {profile.activity_level.value}. Use this context when helpful."
            )
        return (
            "You are a friendly Telegram meal assistant. Talk naturally like an LLM chat assistant. "
            "Use the available tools when the user asks about today's meals, monthly progress, or nutrition advice. "
            "Keep answers concise, practical, and supportive."
            + profile_context
        )

    def _fallback_reply(self, user_text: str) -> str:
        lowered_text = user_text.lower()
        if "meal" in lowered_text or "food" in lowered_text or "calorie" in lowered_text:
            return "I can help with meal tracking, calorie estimates, and daily summaries. Send me a photo or ask about today's intake."
        return "I'm your meal tracking assistant. Ask me anything about food, goals, or today's intake."
