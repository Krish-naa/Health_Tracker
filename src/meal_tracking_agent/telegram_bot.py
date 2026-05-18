from __future__ import annotations

from datetime import date
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import Settings
from .chat_graph import LangGraphChatService
from .db import Database
from .models import ActivityLevel, Gender, HealthGoal
from .schemas import OnboardingProfile
from .service import MealTrackingService

NAME, GOAL, GENDER, AGE, HEIGHT, WEIGHT, ACTIVITY = range(7)


GOAL_OPTIONS = {
    "1": HealthGoal.lose_weight,
    "2": HealthGoal.gain_muscle,
    "3": HealthGoal.maintain,
    "4": HealthGoal.eat_healthy,
}
GENDER_OPTIONS = {"1": Gender.male, "2": Gender.female, "3": Gender.other}
ACTIVITY_OPTIONS = {
    "1": ActivityLevel.sedentary,
    "2": ActivityLevel.lightly_active,
    "3": ActivityLevel.active,
    "4": ActivityLevel.very_active,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None or update.effective_chat is None:
        return ConversationHandler.END

    with database.session() as session:
        profile = service.get_profile(session, user.id)
        if profile:
            await update.message.reply_text(
                f"Welcome back, {profile.name}. Send a meal photo or use /today for your summary."
            )
            return ConversationHandler.END

    await update.message.reply_text("Welcome to Meal Tracking Agent. What is your name?")
    return NAME


async def capture_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["profile"] = {"name": update.message.text.strip()}
    await update.message.reply_text(
        "Choose your goal:\n1) Lose Weight\n2) Gain Muscle\n3) Maintain\n4) Eat Healthy"
    )
    return GOAL


async def capture_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    if choice not in GOAL_OPTIONS:
        await update.message.reply_text("Please reply with 1, 2, 3, or 4.")
        return GOAL
    context.user_data["profile"]["goal"] = GOAL_OPTIONS[choice]
    await update.message.reply_text("Choose your gender:\n1) Male\n2) Female\n3) Other")
    return GENDER


async def capture_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    if choice not in GENDER_OPTIONS:
        await update.message.reply_text("Please reply with 1, 2, or 3.")
        return GENDER
    context.user_data["profile"]["gender"] = GENDER_OPTIONS[choice]
    await update.message.reply_text("Enter your age in years.")
    return AGE


async def capture_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["profile"]["age"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a valid age number.")
        return AGE
    await update.message.reply_text("Enter your height in cm.")
    return HEIGHT


async def capture_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["profile"]["height_cm"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a valid height number.")
        return HEIGHT
    await update.message.reply_text("Enter your weight in kg.")
    return WEIGHT


async def capture_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["profile"]["weight_kg"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a valid weight number.")
        return WEIGHT
    await update.message.reply_text(
        "Choose your activity level:\n1) Sedentary\n2) Lightly Active\n3) Active\n4) Very Active"
    )
    return ACTIVITY


async def capture_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    if choice not in ACTIVITY_OPTIONS:
        await update.message.reply_text("Please reply with 1, 2, 3, or 4.")
        return ACTIVITY

    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return ConversationHandler.END

    profile_payload = context.user_data.pop("profile")
    profile = OnboardingProfile(
        telegram_user_id=user.id,
        chat_id=chat.id,
        name=profile_payload["name"],
        goal=profile_payload["goal"],
        gender=profile_payload["gender"],
        age=profile_payload["age"],
        height_cm=profile_payload["height_cm"],
        weight_kg=profile_payload["weight_kg"],
        activity_level=ACTIVITY_OPTIONS[choice],
    )

    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    with database.session() as session:
        record, sample_plan = service.save_profile(session, profile)

    await update.message.reply_text(
        "Profile created successfully.\n"
        f"Daily targets: {record.calorie_target} kcal, {record.protein_target_g}g protein, "
        f"{record.carbs_target_g}g carbs, {record.fats_target_g}g fats.\n"
        "Sample meal plan:\n- " + "\n- ".join(sample_plan)
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Onboarding cancelled. Send /start when you want to begin again.")
    context.user_data.pop("profile", None)
    return ConversationHandler.END


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None:
        return
    with database.session() as session:
        summary = service.build_daily_summary(session, user.id)
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
    await update.message.reply_text("\n".join(lines))


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None:
        return
    with database.session() as session:
        text = service.build_monthly_summary(session, user.id)
    await update.message.reply_text(text)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = bytes(await file.download_as_bytearray())

    with database.session() as session:
        profile_record = service.get_profile(session, user.id)
        profile = None
        if profile_record:
            profile = OnboardingProfile(
                telegram_user_id=profile_record.telegram_user_id,
                chat_id=profile_record.chat_id,
                name=profile_record.name,
                goal=HealthGoal(profile_record.goal),
                gender=Gender(profile_record.gender),
                age=profile_record.age,
                height_cm=profile_record.height_cm,
                weight_kg=profile_record.weight_kg,
                activity_level=ActivityLevel(profile_record.activity_level),
            )
        analysis, _ = service.analyze_and_log_meal(
            session=session,
            telegram_user_id=user.id,
            profile=profile,
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            file_id=photo.file_id,
        )

    response = [
        f"Logged: {analysis.item_name}",
        f"Calories: {analysis.calories:.0f} kcal",
        f"Protein: {analysis.protein_g:.0f} g | Carbs: {analysis.carbs_g:.0f} g | Fats: {analysis.fats_g:.0f} g",
        f"Portion: {analysis.portion_description}",
    ]
    if analysis.warning:
        response.append(f"Warning: {analysis.warning}")
    if analysis.balance_tip:
        response.append(f"Tip: {analysis.balance_tip}")
    await update.message.reply_text("\n".join(response))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send /start to onboard, then upload meal photos. You can also chat normally with the bot. Use /today for the current day summary and /month for monthly progress."
    )


async def text_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_service: LangGraphChatService = context.application.bot_data["chat_service"]
    meal_service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None or update.message is None:
        return

    with database.session() as session:
        profile_record = meal_service.get_profile(session, user.id)
        profile = None
        if profile_record:
            profile = OnboardingProfile(
                telegram_user_id=profile_record.telegram_user_id,
                chat_id=profile_record.chat_id,
                name=profile_record.name,
                goal=HealthGoal(profile_record.goal),
                gender=Gender(profile_record.gender),
                age=profile_record.age,
                height_cm=profile_record.height_cm,
                weight_kg=profile_record.weight_kg,
                activity_level=ActivityLevel(profile_record.activity_level),
            )

        reply_text = chat_service.reply(
            session=session,
            user_id=user.id,
            user_text=update.message.text,
            thread_id=f"telegram-{user.id}",
            profile=profile,
        )
    await update.message.reply_text(reply_text)


def build_application(
    settings: Settings,
    database: Database,
    service: MealTrackingService,
    chat_service: LangGraphChatService,
) -> Application:
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    application.bot_data["database"] = database
    application.bot_data["service"] = service
    application.bot_data["chat_service"] = chat_service

    onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_name)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_goal)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_age)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_weight)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_activity)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(onboarding)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("month", month))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_chat))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application
