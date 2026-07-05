> **Code the below design.** This document describes the updated Meal Tracking Agent design. Implement it by updating the existing codebase — reuse existing files and functions wherever noted, and add only the new functions/tables explicitly listed. Do not build anything outside what's described here.

# Meal Tracking Agent — High-Level Design (HLD) Document — Revised

Revision note: adds a working interactive menu, profile editing, and entry editing on top of the existing codebase. No unrelated features added — only what's needed to make these work.

---

## 1. Executive Summary

The Meal Tracking Agent is a Telegram-first AI assistant that lets a user track meals by sending photos and natural language messages. It combines the Telegram Bot API, LangGraph ReAct orchestration, LangChain model wrappers, Anthropic vision analysis, lightweight retrieval, SQLite persistence, and scheduled reporting into a conversational nutrition assistant. This revision adds a fully working interactive button menu, the ability to edit a profile at any time, and the ability to edit or delete previously logged entries — using the existing files and functions wherever possible.

- Primary user interaction channel: Telegram chat, now including a persistent inline-button menu.
- Primary AI capabilities: photo-based meal analysis and normal LLM chat.
- Primary persistence layer: SQLite database.
- Primary orchestration style: LangGraph ReAct agent for chat and tool use.
- Primary reporting capability: daily 11 PM progress reports and monthly summaries.
- **New in this revision:** a working main menu, profile re-editing, and entry editing/deleting.

---

## 2. Purpose and Scope

- Track meals without forcing the user to manually enter calories.
- Estimate calories, protein, carbohydrates, and fats from meal photos.
- Provide a conversational interface for general nutrition questions and meal-related guidance.
- Calculate personalized intake targets based on goal, age, gender, height, weight, and activity level.
- Persist meal logs and user profiles so the assistant can summarize daily and monthly progress.
- Send automated daily reports at a configured hour.
- **(New)** Let the user reach every everyday action — logging, viewing, and editing — through a persistent, tappable menu instead of only text commands.
- **(New)** Let the user correct or update their profile at any time, not only once during first-time onboarding.
- **(New)** Let the user correct or remove a previously logged entry instead of it staying wrong forever.

---

## 3. System Overview

The system is organized into five layers: Telegram interface, application orchestration, AI reasoning/analysis, data storage, and scheduler/reporting. This revision adds a menu-dispatch layer inside the Telegram interface: every button tap is a callback that gets routed to the right existing (or newly added) function, so the menu is a thin routing layer on top of logic that mostly already exists.

### 3.1 Overall Architecture Diagram (Updated)

```
Telegram User
   |
   v
Telegram Bot API
   |
   v
telegram_bot.py  ----->  chat_graph.py (LangGraph ReAct)
   |     |                   |
   |     |                   +-----> knowledge_base.py (retrieval)
   |     |                   +-----> service.py (daily/monthly summary tools)
   |     |
   |     +--> menu_callback_handler()  <-- NEW: routes every button tap
   |             |
   |             +--> existing functions (today(), month(), help_command(), sample_meal_plan())
   |             +--> new mini-flows (log water, log exercise, edit entry, edit profile)
   |
   +-----> anthropic_client.py (meal photo vision analysis)
   |
   v
db.py + models.py + schemas.py + nutrition.py
   |
   v
SQLite Database
   |
   v
scheduler.py -> daily report at configured time
```

This shows the menu handler as a new, thin dispatch layer inside `telegram_bot.py` — it doesn't replace any existing subsystem, it just gives the existing subsystems a working button-driven entry point alongside the existing text commands.

### 3.2 Meal Photo Processing Flow (Unchanged)

```
User sends meal photo in Telegram
   |
   v
telegram_bot.handle_photo()
   |
   v
meal_service.get_profile()
   |
   v
anthropic_client.ClaudeMealAnalyzer.analyze()
   |
   v
MealAnalysis JSON-like object
   |
   v
db.add_meal_entry()
   |
   v
Telegram reply with calories/macros/warning/tip
```

### 3.3 Normal Chat / ReAct Flow (Unchanged, Now Entered via a Router)

```
User sends text in Telegram
   |
   v
telegram_bot.route_free_text()   <-- NEW thin wrapper
   |
   +-- if a menu mini-flow is waiting for input -> handle that input
   |
   +-- otherwise -> telegram_bot.text_chat() (unchanged)
            |
            v
      LangGraphChatService.reply()
            |
            v
      create_react_agent()
            |
            +--> today_summary tool
            +--> month_summary tool
            +--> nutrition_guidance_search tool
            |
            v
      LLM final answer -> Telegram reply
```

`text_chat()` itself is not modified — `route_free_text()` sits in front of it so free-form chat keeps working exactly as before whenever no menu mini-flow is waiting for an answer.

### 3.4 Daily Report Flow (Unchanged)

```
scheduler.register_daily_report_job()
   |
   v
11 PM job triggers
   |
   v
send_daily_reports()
   |
   v
list_profiles()
   |
   v
service.build_daily_report_text()
   |
   v
Telegram send_message() to each user
```

### 3.5 Interactive Menu Flow (New)

```
User taps a button (e.g. 'Log water')
   |
   v
Telegram sends a callback_query update
   |
   v
telegram_bot.menu_callback_handler()
   |
   v
await query.answer()   <-- must always happen first (see Section 14)
   |
   v
Read query.data (e.g. 'menu:log_water')
   |
   v
Dispatch to the matching function:
   - immediate-reply buttons -> reply right away (View today, Summary, History, Get tips,
     Diet plan, Help)
   - multi-step buttons -> set context.user_data['awaiting'] and prompt for the next
     message (Log meal, Log water, Log exercise, Edit an entry, Edit your profile)
```

---

## 4. Technologies and Their Roles

Unchanged from the original design — Telegram Bot API (python-telegram-bot), LangGraph, LangChain, Anthropic API, SQLAlchemy/SQLite, and APScheduler-style job queue. This revision uses only what python-telegram-bot already ships: `InlineKeyboardMarkup`/`InlineKeyboardButton` for the menu, and `CallbackQueryHandler` to receive taps — no new library is required.

## 5. Configuration and Environment Variables

Unchanged. No new environment variables are required for the menu, profile-edit, or entry-edit features — they run entirely on existing configuration.

---

## 6. File-by-File Breakdown (Updated)

Files not listed below (`main.py`, `config.py`, `anthropic_client.py`, `knowledge_base.py`, `chat_graph.py`, `scheduler.py`, `__init__.py`) are unchanged in this revision.

### `models.py`

Purpose: unchanged — database schema definitions and core enums.

- `MealEntry` already has a primary-key `id` column via SQLAlchemy by default — this is what makes editing and deleting a specific entry possible; no change needed here to get an ID.
- **[UPDATED]** Add a nullable `edited_at` timestamp column to `MealEntry` so the bot can optionally tell the user "edited 2 hours ago."
- **[NEW]** Add two small new tables, `WaterEntry` and `ExerciseEntry` (user id, amount/duration, timestamp), since these log types don't exist yet in the current schema.

### `schemas.py`

- **[NEW]** Add a lightweight `WaterEntryDTO` and `ExerciseEntryDTO` for passing values between the Telegram layer and `db.py`, mirroring how `MealAnalysis` is already used.

### `db.py`

Purpose: unchanged — database access layer. This revision adds the functions needed to look up, change, and remove a single entry, plus simple water/exercise logging, since today the file only supports adding and aggregating meals.

- **[NEW]** `get_meal_entry(entry_id)` — fetch one meal entry by its id, used when the user selects an entry to edit.
- **[NEW]** `update_meal_entry(entry_id, **fields)` — apply a field-level correction (food description, calories, protein, carbs, fats, or photo reference) to an existing row and set `edited_at`.
- **[NEW]** `delete_meal_entry(entry_id)` — remove a row entirely, used for the "delete this entry" option.
- **[NEW]** `meals_recent(user_id, limit=6)` — return the last N logged meals for a user, used to build the tappable list in the Edit-an-entry and History flows.
- **[NEW]** `add_water_entry(user_id, glasses)` — insert a water log row for today.
- **[NEW]** `add_exercise_entry(user_id, description, minutes)` — insert an exercise log row for today.

Because `meal_totals_for_date()` already recalculates from the current rows in the table every time it's called (rather than from a cached value), an edited or deleted entry is automatically reflected in every future summary with no extra work — this was confirmed against the existing implementation, so no change is needed there.

### `service.py`

No changes required — `build_daily_summary()`, `build_monthly_summary()`, and `build_daily_report_text()` already read live data from `db.py`, so they automatically pick up edits made through the new Edit-an-entry flow.

### `nutrition.py`

No changes required — `sample_meal_plan()` already exists and is reused directly by the new "Diet plan" menu button.

### `telegram_bot.py` — the main file that changes

This is where nearly all new code lives. Existing onboarding functions (`start()`, `capture_name()`, `capture_goal()`, `capture_gender()`, `capture_age()`, `capture_height()`, `capture_weight()`, `capture_activity()`, `cancel()`), existing command handlers (`today()`, `month()`, `help_command()`), and `handle_photo()` are all reused as-is or called from new wrapper functions — they are **not** rewritten.

- **[NEW]** `build_main_menu()` — builds the `InlineKeyboardMarkup` shown after `/start` and after most replies, matching the existing menu layout plus the new "Edit my profile" button. Each button's `callback_data` uses a `menu:` prefix (e.g. `menu:log_water`).
- **[NEW]** `menu_callback_handler(update, context)` — registered as the app's `CallbackQueryHandler`. Always calls `await query.answer()` first, then reads `query.data` and dispatches to the matching function below. **This single function is the fix for the "nothing happens when I tap a button" issue** — see Section 14.
- **[NEW, thin wrappers around existing logic]** `show_today()`, `show_summary()`, `show_help()`, `show_diet_plan()` — call the existing `today()`, `month()`, `help_command()` logic (refactored slightly so they can be called from either a command or a callback) and existing `sample_meal_plan()`, replying directly with no further input needed.
- **[NEW]** `show_history()` — formats a short list of recent entries (from `db.meals_recent()` and, for a broader view, `meals_for_date()`/`meals_for_month()`) as a readable message.
- **[NEW]** `show_tips()` — builds a short, personalized suggestion by calling `LangGraphChatService.reply()` with a synthetic prompt such as "Give me one quick tip based on my intake so far today" — reuses the existing ReAct agent and its knowledge_base tool rather than duplicating any logic.
- **[NEW]** `start_log_water()`, `start_log_exercise()`, `start_log_meal()` — set `context.user_data['awaiting']` to a marker (e.g. `'log_water'`, `'log_exercise'`, `'meal_text'`) and send a prompt message asking for the next piece of information.
- **[NEW]** `start_edit_entry()`, `handle_edit_entry_selected()`, `handle_edit_field_selected()` — show the user's recent entries as buttons (via `db.meals_recent()`), then the chosen entry's current details and a set of field buttons, then wait for the corrected value via `context.user_data['awaiting']`.
- **[NEW, reuses existing onboarding states]** `start_edit_profile()` — re-enters the exact same onboarding `ConversationHandler` used by `start()`, so all seven existing questions (name, goal, gender, age, height, weight, activity) are reused unchanged; finishing calls the existing `upsert_profile()` and `nutrition.calculate_targets()`, the same as first-time onboarding.
- **[NEW wrapper — replaces the direct text MessageHandler]** `route_free_text(update, context)` — checks `context.user_data.get('awaiting')` first. If a mini-flow is waiting for input, this routes the message to the matching `finish_*` function (`finish_log_water()`, `finish_log_exercise()`, `finish_edit_value()`, `finish_meal_text()`) and then clears the flag. If nothing is waiting, it calls the existing `text_chat()` exactly as before.
- **[UPDATED]** `build_application()` — register `CallbackQueryHandler(menu_callback_handler)`; add the same onboarding `ConversationHandler` as an additional entry point triggered by the `menu:edit_profile` callback, not only by `/start`; point the general text `MessageHandler` at `route_free_text()` instead of `text_chat()` directly.

---

## 7. Detailed Workflows (Updated)

- Onboarding: User sends `/start` -> bot collects profile values -> nutrition targets are calculated -> profile is stored. *(Unchanged.)*
- Meal logging via photo: User sends a meal photo -> photo is analyzed by Anthropic -> meal is stored -> bot returns calories/macros/warnings. *(Unchanged.)*
- Normal chat: User sends free text with no mini-flow waiting -> LangGraph ReAct agent evaluates the request -> tool call is selected if needed -> reply is returned. *(Unchanged, now reached via `route_free_text()`.)*
- Daily reporting: Scheduled job triggers at 11 PM -> all profiles are loaded -> a summary is sent to each Telegram chat. *(Unchanged.)*
- **(New)** Menu-driven logging: User taps "Log water" or "Log exercise" -> bot asks one follow-up question -> user answers in plain text -> `route_free_text()` detects the waiting flow -> entry is saved -> bot confirms with the updated daily total.
- **(New)** Profile editing: User taps "Edit my profile" at any time -> the same seven onboarding questions are asked again -> answers overwrite the existing profile via `upsert_profile()` -> new targets are calculated and shown.
- **(New)** Entry editing: User taps "Edit an entry" -> recent entries are shown as buttons -> user picks one -> user picks a field -> user sends the corrected value -> the row is updated in place -> the bot confirms with the corrected entry and updated totals.

---

## 8. Data Model and Storage Design (Updated)

The system still uses SQLite for local persistence, kept intentionally simple.

- `UserProfile` has a unique Telegram user id to prevent duplicate profiles — editing a profile updates this same row via `upsert_profile()` rather than creating a second row.
- `MealEntry` is time-series data; each row is one logged meal, and each row already has a primary-key `id` — this is what the Edit-an-entry flow references when a user picks which entry to fix.
- A nullable `edited_at` column is added to `MealEntry` so an edited row can be distinguished from an original one if ever needed.
- Two new small tables, `WaterEntry` and `ExerciseEntry`, store the new log types introduced by the menu; both follow the same simple, single-user-id-plus-timestamp pattern as `MealEntry`.
- The analysis response is preserved as raw JSON text for traceability, unchanged.

---

## 9. Error Handling and Fallback Strategy (Updated)

- If Anthropic meal analysis is unavailable, the assistant returns a safe default nutrition estimate. *(Unchanged.)*
- If the LLM chat provider throws an API error, the chat layer falls back to a local response instead of crashing the bot. *(Unchanged.)*
- If no profile exists, summaries still work but clearly tell the user to onboard first. *(Unchanged.)*
- If a Telegram send operation fails for a user, the scheduler continues with the remaining users. *(Unchanged.)*
- **(New)** Every `callback_query` is answered with `query.answer()` immediately inside `menu_callback_handler()`, even if the underlying action later fails — this prevents Telegram from showing a stuck loading state on the button, which is part of why buttons can appear to "do nothing."
- **(New)** If a user taps a button mid-way through another unfinished mini-flow (e.g. taps "Log water" while "Edit an entry" is still waiting for a value), the new flow simply overwrites `context.user_data['awaiting']` and the old one is abandoned cleanly rather than causing a conflicting state.

## 10. Security and Operational Notes

Unchanged — secrets stay in `.env`, the bot runs in polling mode with a single instance, and Telegram user/chat ids correlate messages with profiles.

## 11. What Each Major External Service Does

Unchanged from the original design.

## 12. Summary

The Meal Tracking Agent remains a modular Telegram-based AI product. This revision closes the gap between the menu the user already sees and working functionality behind it: every button now has a registered handler, multi-step actions (logging water/exercise, editing an entry, editing a profile) are handled through a simple "awaiting input" pattern layered on top of the existing text-chat router, and every new feature reuses existing business logic (`db.py`, `service.py`, `nutrition.py`) rather than duplicating it.

## 13. Future Enhancements

- ~~Interactive main menu with working buttons~~ — **DONE, addressed in this revision.**
- ~~Profile editing at any time~~ — **DONE, addressed in this revision.**
- ~~Entry editing and deleting~~ — **DONE, addressed in this revision.**
- Persist LangGraph chat memory in SQLite so conversations survive restarts — still future; see the separate AIM Implementation HLD.
- Replace the simple keyword knowledge base with real vector-based RAG — still future; see the separate AIM Implementation HLD.
- Add image storage or object storage for meal photos — still future; see the separate AIM Implementation HLD.
- Add admin dashboards and export functionality for coaches or nutritionists — still future; see the separate AIM Implementation HLD.
- Support deployment through webhook mode and containerization — still future.

---

## 14. Known Issue in the Current Build: Why Tapping a Menu Button Does Nothing

Based on the screenshot of the current bot, the menu is already visually present, but tapping a button produces no visible effect. This matches a specific, common cause in python-telegram-bot: the buttons are being sent as an `InlineKeyboardMarkup`, but the application never registers a `CallbackQueryHandler` to receive the tap, and/or the handler never calls `await query.answer()`. When neither happens, Telegram receives the tap but the bot never reacts, and the loading indicator on the button can appear to just hang or silently reset — which reads to the user as "nothing happening."

### The Fix

1. Add `app.add_handler(CallbackQueryHandler(menu_callback_handler))` inside `build_application()`, alongside the existing command and message handlers.
2. Inside `menu_callback_handler()`, the very first line must be `await update.callback_query.answer()` — this tells Telegram the tap was received, regardless of what happens next.
3. Only after answering, read `update.callback_query.data` and dispatch to the correct function using the table in Section 15.

---

## 15. Interactive Main Menu — Button-by-Button Behavior

| Button label | `callback_data` | Handler function | Behavior | Reuses |
|---|---|---|---|---|
| Log meal | `menu:log_meal` | `start_log_meal()` | Prompts for a photo (or a typed description); saves via existing flow | `handle_photo()`, `analyze_and_log_meal()` |
| Log water | `menu:log_water` | `start_log_water()` -> `finish_log_water()` | Asks for a number, saves as a new row | New: `add_water_entry()` |
| Log exercise | `menu:log_exercise` | `start_log_exercise()` -> `finish_log_exercise()` | Asks for description + duration, saves as a new row | New: `add_exercise_entry()` |
| Edit entry | `menu:edit_entry` | `start_edit_entry()` -> `handle_edit_entry_selected()` -> `handle_edit_field_selected()` -> `finish_edit_value()` | Pick entry -> pick field -> send new value -> confirmed | New: `get_meal_entry()`, `update_meal_entry()`, `meals_recent()` |
| View today | `menu:view_today` | `show_today()` | Immediate reply | Existing: `build_daily_summary()` |
| Summary | `menu:summary` | `show_summary()` | Immediate reply | Existing: `build_monthly_summary()` |
| History | `menu:history` | `show_history()` | Immediate reply, includes entry IDs for quick editing | Existing: `meals_for_date()`, `meals_for_month()` |
| Get tips | `menu:tips` | `show_tips()` | Immediate reply, generated live | Existing: `LangGraphChatService.reply()` |
| Diet plan | `menu:diet_plan` | `show_diet_plan()` | Immediate reply | Existing: `nutrition.sample_meal_plan()` |
| Help | `menu:help` | `show_help()` | Immediate reply | Existing: `help_command()` |
| Edit my profile | `menu:edit_profile` | `start_edit_profile()` | Re-enters the 7-question onboarding flow | Existing: onboarding `ConversationHandler`, `upsert_profile()` |

---

## 16. Log Meal / Log Water / Log Exercise Flows

Log water example (Log meal / Log exercise follow the same shape):

```
User taps 'Log water'
   |
   v
start_log_water(): sets context.user_data['awaiting'] = 'log_water'
   |                  sends 'How many glasses of water did you have?'
   v
User replies with a number, e.g. '3'
   |
   v
route_free_text() sees 'awaiting' == 'log_water'
   |
   v
finish_log_water(): parses the number, calls db.add_water_entry()
   |
   v
Bot confirms: 'Logged 3 glasses of water. Today's total: 6 glasses.'
```

Log meal via the menu works the same way but simply prompts the user to send a photo — if a photo arrives, the existing `handle_photo()` runs exactly as it does today; if the user types a description instead, `finish_meal_text()` passes that description into the existing `analyze_and_log_meal()` as a text-based meal instead of an image.

---

## 17. Edit an Entry Flow

| Step | What happens |
|---|---|
| 1 | User taps 'Edit entry'. `start_edit_entry()` calls `db.meals_recent(user_id, limit=6)` and shows each as a button labeled with a short summary (e.g. 'Breakfast - 8:03 AM - ~450 kcal'). |
| 2 | User taps an entry. `handle_edit_entry_selected()` calls `db.get_meal_entry(entry_id)` and shows its full details, plus buttons for 'Food description', 'Calories', 'Protein/Carbs/Fats', 'Delete entry'. |
| 3 | User taps a field. `handle_edit_field_selected()` sets `context.user_data['awaiting'] = 'edit_value:<entry_id>:<field>'` and asks for the corrected value (skipped entirely for 'Delete entry', which goes straight to a confirmation prompt). |
| 4 | User sends the corrected value as plain text. `route_free_text()` detects the `edit_value:` prefix and calls `finish_edit_value()`, which calls `db.update_meal_entry(entry_id, field=value)` and sets `edited_at`. |
| 5 | Bot confirms with the corrected entry and the updated daily total (recomputed live via the existing `meal_totals_for_date()`, so no separate recalculation step is needed). |

Delete uses the same entry-selection step but skips straight to a yes/no confirmation button pair before calling `db.delete_meal_entry(entry_id)` — never triggered by a plain text reply, to avoid an accidental deletion from a stray message.

---

## 18. Edit Your Profile Flow

```
User taps 'Edit my profile' (works even though they're already registered)
   |
   v
start_edit_profile() enters the SAME ConversationHandler states
   used by /start: NAME -> GOAL -> GENDER -> AGE -> HEIGHT -> WEIGHT -> ACTIVITY
   |
   v
capture_name() ... capture_activity()   <-- all reused unchanged
   |
   v
capture_activity() calls the existing upsert_profile() and
nutrition.calculate_targets(), same as first-time onboarding
   |
   v
Bot shows the newly recalculated daily calorie/macro targets
```

Because `upsert_profile()` already inserts or updates based on the Telegram user id, running onboarding a second time naturally overwrites the existing profile instead of creating a duplicate — no new database logic is required for this flow, only a second way to enter the same conversation.

---

## 19. Updated Welcome Message

The current welcome text is plain and doesn't invite interaction. A more interactive version to use in `start()` when building the menu:

```
Hey! I'm your Meal Tracking Agent.
Snap a meal photo, log water or a workout, or just ask me a nutrition question —
I'll take it from there. Tap an option below to get started.
```

Keep it short, keep the tone friendly and direct, and make sure the menu (`build_main_menu()`) is attached to this same message so the buttons appear immediately under it.

---

## 20. Consolidated Checklist for Copilot

| File | Changes to make |
|---|---|
| `telegram_bot.py` | Add `build_main_menu()`, `menu_callback_handler()`, `show_today()`, `show_summary()`, `show_history()`, `show_tips()`, `show_diet_plan()`, `show_help()`, `start_log_water()`/`finish_log_water()`, `start_log_exercise()`/`finish_log_exercise()`, `start_log_meal()`/`finish_meal_text()`, `start_edit_entry()`/`handle_edit_entry_selected()`/`handle_edit_field_selected()`/`finish_edit_value()`, `start_edit_profile()`, `route_free_text()`. Update `build_application()` to register the `CallbackQueryHandler`, add the edit-profile entry point to the onboarding `ConversationHandler`, and point the text handler at `route_free_text()`. Update the welcome text in `start()`. |
| `db.py` | Add `get_meal_entry()`, `update_meal_entry()`, `delete_meal_entry()`, `meals_recent()`, `add_water_entry()`, `add_exercise_entry()`. |
| `models.py` | Add `edited_at` column to `MealEntry`; add `WaterEntry` and `ExerciseEntry` tables. |
| `schemas.py` | Add `WaterEntryDTO` and `ExerciseEntryDTO` (optional but recommended for consistency with `MealAnalysis`). |
| `service.py`, `nutrition.py`, `chat_graph.py`, `anthropic_client.py`, `knowledge_base.py`, `scheduler.py`, `config.py`, `main.py` | No changes required — all reused as-is. |
