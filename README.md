# 🚀 Meal Tracking Agent

A Telegram-based meal tracking agent that analyzes food photos, logs meals, estimates calories and macros, and sends daily and monthly progress summaries.

## ✨ What This Project Is

This project is a Telegram-first AI assistant for meal tracking and nutrition guidance. Users can:

- onboard once with basic profile details,
- send food photos for nutrition analysis,
- chat normally with the bot like an LLM assistant,
- get a daily report automatically at 11 PM,
- and ask for daily or monthly progress summaries anytime.

The system combines Telegram, LangGraph, LangChain, vision-capable AI models, SQLite, and scheduled jobs.

## 🧭 One-Line Summary

This is a Telegram-first AI meal coach that supports photo-based nutrition analysis, conversational chat, daily automation, and long-term meal tracking.

## 🌟 Features

- 📸 Photo-based meal tracking from Telegram
- 🧠 Meal analysis using Anthropic or OpenAI vision, depending on the configured API key
- 🤖 LangGraph ReAct chat with memory, tools, and lightweight retrieval
- 📝 Onboarding flow for personal goals and profile setup
- 💾 SQLite meal logging and user profiles
- 🗓️ Daily 11 PM progress report
- 📊 Monthly summary reports

## 🔄 How It Works

1. A user starts the bot in Telegram with `/start`.
2. The bot collects onboarding data like name, goal, gender, age, height, weight, and activity level.
3. The nutrition engine calculates a daily calorie and macro target.
4. When a user sends a meal photo, the AI vision model analyzes the image and returns calories, protein, carbs, fats, warnings, and tips.
5. Each meal is saved to SQLite with a timestamp.
6. When a user sends normal text, LangGraph routes the message through a ReAct agent that can call summary and retrieval tools.
7. A scheduled job sends a daily summary at 11 PM.

## 🏗️ Architecture Summary

- `telegram_bot.py` handles Telegram commands, onboarding, photo uploads, and normal chat routing.
- `chat_graph.py` manages LangGraph ReAct chat and tool calling.
- `anthropic_client.py` handles meal photo analysis using Anthropic or OpenAI vision.
- `service.py` contains the business logic that ties the AI, database, and summary flows together.
- `db.py` stores and reads user profiles and meal logs.
- `scheduler.py` sends the daily report.
- `knowledge_base.py` provides lightweight nutrition retrieval for chat guidance.

## 📁 Project Structure

- `src/meal_tracking_agent/config.py` — environment configuration
- `src/meal_tracking_agent/db.py` — database setup and repositories
- `src/meal_tracking_agent/models.py` — data models and enums
- `src/meal_tracking_agent/nutrition.py` — calorie and macro calculations
- `src/meal_tracking_agent/anthropic_client.py` — Claude integration
- `src/meal_tracking_agent/chat_graph.py` — LangGraph ReAct chat assistant
- `src/meal_tracking_agent/knowledge_base.py` — local retrieval knowledge base for nutrition guidance
- `src/meal_tracking_agent/telegram_bot.py` — Telegram bot handlers
- `src/meal_tracking_agent/scheduler.py` — daily report scheduling
- `src/meal_tracking_agent/main.py` — application entry point
- `src/meal_tracking_agent/schemas.py` — typed request/response models
- `src/meal_tracking_agent/nutrition.py` — calorie and macro math
- `src/meal_tracking_agent/anthropic_client.py` — vision-based meal analysis adapter
- `src/meal_tracking_agent/service.py` — orchestration and reporting logic

## ⚙️ Setup

1. Create and activate the project virtual environment.
2. Install dependencies:

```bash
pip install -e .
```

3. Create a `.env` file in the project root and add the required keys listed below.
4. Start the bot:

```bash
python -m meal_tracking_agent.main
```

### 🔐 Required Environment Variables

- `TELEGRAM_BOT_TOKEN` — token from BotFather
- `ANTHROPIC_API_KEY` — optional, enables Anthropic-based meal analysis
- `OPENAI_API_KEY` — optional, enables OpenAI-based chat and meal analysis fallback
- `DATABASE_URL` — defaults to `sqlite:///./meal_tracking.db`
- `TIMEZONE` — used for summary dates and the daily scheduler
- `DAILY_REPORT_HOUR` and `DAILY_REPORT_MINUTE` — daily report time
- `ANTHROPIC_MODEL` — Anthropic model name
- `OPENAI_MODEL` — OpenAI model name
- `LLM_PROVIDER` — `auto`, `openai`, or `anthropic`

### 🧩 Recommended Local Files

- `.env` — your private secrets and runtime config
- `.venv` — project Python environment
- `meal_tracking.db` — local SQLite database

### 🖥️ Notes on Environment Selection

- The project currently expects Python 3.9+.
- Use the `.venv` interpreter for the workspace to avoid import mismatch issues.
- If VS Code shows stale import errors, reload the window after switching the interpreter.

## 🤖 Telegram Bot Flow

- `/start` begins onboarding
- The bot collects name, goal, gender, age, height, weight, and activity level
- Photos are analyzed and logged as meals
- Normal text messages are routed to a LangGraph ReAct agent
- `/today` returns the current day’s summary
- `/month` returns a monthly summary

## 💾 Data Storage

The app stores data in SQLite by default.

- `user_profiles` — one row per Telegram user, including targets and onboarding details
- `meal_entries` — one row per logged meal, including nutrition totals and raw analysis payload

If you change `DATABASE_URL` to PostgreSQL later, the business logic remains the same.

## 🛠️ Troubleshooting

- If meal photos keep returning the same estimate, make sure either `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is valid.
- If the bot does not start, confirm that `TELEGRAM_BOT_TOKEN` is set.
- If the bot runs but does not answer, ensure only one polling instance is running.
- If VS Code shows unresolved imports, select the project `.venv` interpreter and reload the window.

## 📝 Notes

- The meal-photo AI layer supports Anthropic and OpenAI vision.
- The chat layer uses LangGraph ReAct plus a small local knowledge base.
- The scheduler is designed for an 11 PM daily progress report in the configured timezone.
- SQLite is the default persistence layer, but you can switch to PostgreSQL later.
- The project is designed to be extended with real RAG/vector search, chat memory persistence, and deployment tooling.

## ✅ Quick Review Highlights

- Clean Telegram onboarding flow
- Tool-using LLM chat with LangGraph ReAct
- Vision-based meal analysis with fallback safety
- Local SQLite storage for simple development and demos
- Clear extension points for future RAG, persistence, and deployment
