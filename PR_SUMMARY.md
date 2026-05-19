# 🚀 Meal Tracking Agent — PR Summary

## ✨ What’s New
- 📸 **Meal photo intelligence** — analyzes food photos and estimates calories, protein, carbs, and fats.
- 🤖 **LangGraph ReAct chat** — users can chat naturally and the bot can call tools when needed.
- 🧠 **Lightweight retrieval** — nutrition guidance search is powered by a local knowledge base.
- 🗓️ **Daily automation** — 11 PM meal progress report sent automatically.
- 💾 **SQLite persistence** — user profiles and meal logs are stored locally.
- ⚙️ **Workspace-ready settings** — VS Code is pinned to the project `.venv` so imports resolve correctly.

## 🔍 Files to Review
- [README.md](README.md) — full project overview, setup, architecture, troubleshooting, and flow.
- [src/meal_tracking_agent/chat_graph.py](src/meal_tracking_agent/chat_graph.py) — LangGraph ReAct agent and tools.
- [src/meal_tracking_agent/anthropic_client.py](src/meal_tracking_agent/anthropic_client.py) — meal photo vision analysis.
- [.vscode/settings.json](.vscode/settings.json) — project interpreter configuration.
- [.env.example](.env.example) — sample environment variables.

## 🧭 Flow at a Glance
1. 🙋 User starts the bot with `/start`
2. 📝 Bot collects onboarding details
3. 🧮 Targets are calculated from profile data
4. 📷 Meal photo is analyzed by Anthropic or OpenAI vision
5. 💾 Meal is logged in SQLite
6. 💬 Normal text is routed through LangGraph ReAct chat
7. 📈 Daily and monthly summaries are generated

## 🎯 Why This Matters
This update makes the bot feel like a real AI product instead of a simple command bot: it supports normal conversation, photo-based meal logging, automated summaries, and cleaner local development setup.

## 🧪 Validation
- ✅ Project imports work under `.venv`
- ✅ Pylance/workspace settings updated to the correct interpreter
- ✅ Bot startup path is clean

## 📝 Notes for Reviewers
- 🔐 API keys are kept out of source control
- 🧩 Chat and vision are separated into dedicated modules
- 📦 The project stays lightweight with SQLite by default
- 🚀 Ready for future upgrades like persistent chat memory, real RAG, and deployment support
