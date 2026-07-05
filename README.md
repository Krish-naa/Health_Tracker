# Meal Tracking Agent

This project is a free Telegram bot for meal tracking. It uses Python, the Telegram Bot API, and SQLite only.

## What it does
- Walks new users through a guided registration flow
- Logs meals, water, and exercise
- Shows daily totals versus calorie targets
- Displays recent history and helpful tips
- Lets users edit or delete a previously logged meal entry

## Run guide

### 1) Prerequisites
- Python 3.10 or higher
- A Telegram account
- A Telegram bot token from BotFather

### 2) Setup
```bash
cd c:\krishna\Project_Telegram_Chat_Bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project folder with:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DB_PATH=meal_tracking.db
```

### 3) Run the bot
```bash
python src/meal_tracking_agent/main.py
```

### 4) Use the bot
Open Telegram and start the bot with these commands:
- `/start` for the main menu
- `/register` to start the guided onboarding flow
- `/addmeal` to log a meal
- `/logwater` to log water
- `/logexercise` to log exercise
- `/edit` to update or remove a past meal entry
- `/summary` or `/history` for quick reviews
- `/help` for the command list

## Notes
- No paid services are required for the basic version.
- Data is stored locally in SQLite.
- If you deploy later, a free host such as Render or Railway can be used.
