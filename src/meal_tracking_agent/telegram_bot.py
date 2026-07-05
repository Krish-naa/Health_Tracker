from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import Settings
from .chat_graph import LangGraphChatService
from .db import (
    Database,
    add_exercise_entry,
    add_water_entry,
    delete_meal_entry,
    get_meal_entry,
    meals_recent,
    update_meal_entry,
)
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


def build_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Log meal", callback_data="menu:log_meal")],
        [InlineKeyboardButton("Log water", callback_data="menu:log_water")],
        [InlineKeyboardButton("Log exercise", callback_data="menu:log_exercise")],
        [InlineKeyboardButton("Edit entry", callback_data="menu:edit_entry")],
        [InlineKeyboardButton("View today", callback_data="menu:view_today")],
        [InlineKeyboardButton("Summary", callback_data="menu:summary")],
        [InlineKeyboardButton("History", callback_data="menu:history")],
        [InlineKeyboardButton("Get tips", callback_data="menu:tips")],
        [InlineKeyboardButton("Diet plan", callback_data="menu:diet_plan")],
        [InlineKeyboardButton("Help", callback_data="menu:help")],
        [InlineKeyboardButton("Edit my profile", callback_data="menu:edit_profile")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None or update.effective_chat is None:
        return ConversationHandler.END

    with database.session() as session:
        profile = service.get_profile(session, user.id)
        if profile and not context.user_data.get("editing_profile"):
            await _reply_text(
                update,
                f"Welcome back, {profile.name}. Send a meal photo or use /today for your summary.",
                reply_markup=build_main_menu(),
            )
            return ConversationHandler.END

    await _reply_text(
        update,
        "Hey! I'm your Meal Tracking Agent.\n"
        "Snap a meal photo, log water or a workout, or just ask me a nutrition question —\n"
        "I'll take it from there. Tap an option below to get started.",
        reply_markup=build_main_menu(),
    )
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

    context.user_data.pop("editing_profile", None)
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
    await _reply_text(update, "\n".join(lines))


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None:
        return
    with database.session() as session:
        text = service.build_monthly_summary(session, user.id)
    await _reply_text(update, text)


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
    await _reply_text(
        update,
        "Send /start to onboard, then upload meal photos. You can also chat normally with the bot. Use /today for the current day summary and /month for monthly progress.",
    )


async def _reply_text(update: Update, text: str, **kwargs: Any) -> None:
    if getattr(update, "callback_query", None) and getattr(update.callback_query, "message", None):
        await update.callback_query.message.reply_text(text, **kwargs)
        return
    if getattr(update, "message", None):
        await update.message.reply_text(text, **kwargs)
        return
    raise RuntimeError("No message target available for reply")


async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await today(update, context)


async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await month(update, context)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await help_command(update, context)


async def show_diet_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from .nutrition import sample_meal_plan

    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None:
        return
    with database.session() as session:
        profile = service.get_profile(session, user.id)
    if profile is None:
        await _reply_text(update, "Create your profile first with /start so I can tailor a diet plan.")
        return
    plan = sample_meal_plan(HealthGoal(profile.goal))
    await _reply_text(update, "Sample meal plan:\n- " + "\n- ".join(plan))


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None:
        return
    with database.session() as session:
        recent = meals_recent(session, user.id, limit=6)
    if not recent:
        await _reply_text(update, "No meals logged yet.")
        return
    lines = [f"Recent entries for {user.id}:"]
    for meal in recent:
        lines.append(f"{meal.id}: {meal.meal_name} — {meal.calories:.0f} kcal ({meal.eaten_at.strftime('%H:%M')})")
    await _reply_text(update, "\n".join(lines))


async def show_tips(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_service: LangGraphChatService = context.application.bot_data["chat_service"]
    meal_service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None:
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
            user_text="Give me one quick tip based on my intake so far today",
            thread_id=f"telegram-tips-{user.id}",
            profile=profile,
        )
    await _reply_text(update, reply_text)


async def start_log_water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting"] = "log_water"
    await _reply_text(update, "How many glasses of water did you have?")


async def start_log_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting"] = "log_exercise"
    await _reply_text(update, "How many minutes did you exercise? Please reply with a short description and minutes, for example: 'Walk 30'.")


async def start_log_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting"] = "meal_text"
    await _reply_text(update, "Please send a photo or describe the meal in a few words.")


async def finish_log_water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None or update.message is None:
        return
    try:
        glasses = float(update.message.text.strip())
    except (AttributeError, ValueError):
        await _reply_text(update, "Please enter a number of glasses.")
        return
    with database.session() as session:
        entry = add_water_entry(session, user.id, glasses)
    await _reply_text(update, f"Logged {entry.glasses} glasses of water.")


async def finish_log_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None or update.message is None:
        return
    text = update.message.text.strip()
    parts = text.rsplit(" ", 1)
    if len(parts) != 2:
        await _reply_text(update, "Please reply like 'Walk 30'.")
        return
    description, minute_text = parts
    try:
        minutes = int(minute_text)
    except ValueError:
        await _reply_text(update, "Please reply like 'Walk 30'.")
        return
    with database.session() as session:
        entry = add_exercise_entry(session, user.id, description, minutes)
    await _reply_text(update, f"Logged {entry.description} for {entry.minutes} minutes.")


async def finish_meal_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service: MealTrackingService = context.application.bot_data["service"]
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None or update.message is None:
        return
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
            image_bytes=b"",
            mime_type="image/jpeg",
            file_id=None,
        )
    await _reply_text(update, f"Logged: {analysis.item_name} ({analysis.calories:.0f} kcal)")


async def start_edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None:
        return
    with database.session() as session:
        recent = meals_recent(session, user.id, limit=6)
    if not recent:
        await _reply_text(update, "You have no recent meals to edit.")
        return
    keyboard = []
    for meal in recent:
        keyboard.append([InlineKeyboardButton(f"{meal.id}: {meal.meal_name}", callback_data=f"menu:edit_entry:{meal.id}")])
    await _reply_text(update, "Choose an entry to edit:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_edit_entry_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    parts = query.data.split(":")
    entry_id_text = parts[2] if len(parts) >= 3 else ""
    database: Database = context.application.bot_data["database"]
    with database.session() as session:
        entry = get_meal_entry(session, int(entry_id_text))
    if entry is None:
        await _reply_text(update, "That entry could not be found.")
        return
    keyboard = [
        [InlineKeyboardButton("Food description", callback_data=f"menu:edit_field:{entry.id}:meal_name")],
        [InlineKeyboardButton("Calories", callback_data=f"menu:edit_field:{entry.id}:calories")],
        [InlineKeyboardButton("Protein/Carbs/Fats", callback_data=f"menu:edit_field:{entry.id}:macros")],
        [InlineKeyboardButton("Delete entry", callback_data=f"menu:delete_entry:{entry.id}")],
    ]
    await _reply_text(update, f"Entry {entry.id}: {entry.meal_name} — {entry.calories:.0f} kcal", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_edit_field_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    parts = query.data.split(":")
    if len(parts) < 4:
        return
    entry_id = int(parts[2])
    field = parts[3]
    if field == "delete_entry":
        return
    if field == "macros":
        context.user_data["awaiting"] = f"edit_value:{entry_id}:macros"
        await _reply_text(update, "Reply with the corrected values as 'protein carbs fats' (for example: '20 50 10').")
        return
    context.user_data["awaiting"] = f"edit_value:{entry_id}:{field}"
    await _reply_text(update, "Send the corrected value.")


async def finish_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["database"]
    user = update.effective_user
    if user is None or update.message is None:
        return
    awaiting = context.user_data.get("awaiting")
    if not isinstance(awaiting, str) or not awaiting.startswith("edit_value:"):
        return
    _, entry_id_text, field = awaiting.split(":", 2)
    entry_id = int(entry_id_text)
    text = update.message.text.strip()
    with database.session() as session:
        if field == "macros":
            parts = text.split()
            if len(parts) != 3:
                await _reply_text(update, "Please reply like '20 50 10'.")
                return
            protein, carbs, fats = (float(parts[0]), float(parts[1]), float(parts[2]))
            update_meal_entry(session, entry_id, protein_g=protein, carbs_g=carbs, fats_g=fats)
        else:
            if field == "calories":
                value = float(text)
            else:
                value = text
            update_meal_entry(session, entry_id, **{field: value})
        entry = get_meal_entry(session, entry_id)
    if entry is None:
        await _reply_text(update, "That entry could not be found.")
        return
    await _reply_text(update, f"Updated entry {entry.id}: {entry.meal_name} — {entry.calories:.0f} kcal")


async def delete_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    parts = query.data.split(":")
    entry_id = int(parts[2]) if len(parts) >= 3 else 0
    database: Database = context.application.bot_data["database"]
    with database.session() as session:
        deleted = delete_meal_entry(session, entry_id)
    if deleted:
        await _reply_text(update, "Entry deleted.")
    else:
        await _reply_text(update, "That entry could not be found.")


async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["editing_profile"] = True
    context.user_data.pop("profile", None)
    await start(update, context)


async def route_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    awaiting = context.user_data.get("awaiting")
    if isinstance(awaiting, str):
        if awaiting == "log_water":
            await finish_log_water(update, context)
        elif awaiting == "log_exercise":
            await finish_log_exercise(update, context)
        elif awaiting == "meal_text":
            await finish_meal_text(update, context)
        elif awaiting.startswith("edit_value:"):
            await finish_edit_value(update, context)
        context.user_data.pop("awaiting", None)
        return
    await text_chat(update, context)


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    data = query.data or ""
    if data == "menu:log_meal":
        await start_log_meal(update, context)
    elif data == "menu:log_water":
        await start_log_water(update, context)
    elif data == "menu:log_exercise":
        await start_log_exercise(update, context)
    elif data == "menu:edit_entry":
        await start_edit_entry(update, context)
    elif data.startswith("menu:edit_entry:"):
        await handle_edit_entry_selected(update, context)
    elif data.startswith("menu:edit_field:"):
        await handle_edit_field_selected(update, context)
    elif data.startswith("menu:delete_entry:"):
        await delete_entry(update, context)
    elif data == "menu:view_today":
        await show_today(update, context)
    elif data == "menu:summary":
        await show_summary(update, context)
    elif data == "menu:history":
        await show_history(update, context)
    elif data == "menu:tips":
        await show_tips(update, context)
    elif data == "menu:diet_plan":
        await show_diet_plan(update, context)
    elif data == "menu:help":
        await show_help(update, context)
    elif data == "menu:edit_profile":
        await start_edit_profile(update, context)


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
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start_edit_profile, pattern="menu:edit_profile"),
        ],
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
    application.add_handler(CallbackQueryHandler(menu_callback_handler))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("month", month))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_free_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application
