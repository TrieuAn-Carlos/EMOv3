# EMO - AI Personal Assistant

AI assistant with Gmail/Calendar integration, persistent memory, and multi-tier context.

## Tech Stack

- **Frontend**: Streamlit
- **AI**: Emo & Google Gemini 2.5 Flash
- **Memory**: ChromaDB (vector DB)
- **Integrations**: Gmail API, Google Calendar API, YouTube Transcript API, Jina Reader

## Quick Start

```bash
source venv/bin/activate
streamlit run main.py
# Open http://localhost:8501
```

## Project Structure

```
├── main.py           # Streamlit UI + chat interface
├── agent.py          # LangGraph agent + system prompt
├── tools.py          # All AI tools (memory, web, youtube)
├── state.py          # Universal Context (4 Pillars)
├── history.py        # Chat session management
├── credential_manager.py  # Google OAuth management
├── emo_memory/       # ChromaDB database
└── .env              # API keys (GEMINI_API_KEY)
```

## Architecture

```
User → Streamlit UI → Gemini (with tools) → Response
                          ↓
              ┌───────────┴───────────┐
              │                       │
         ChromaDB              External APIs
      (3-tier memory)      (Gmail, Calendar, Web)
```

### 4 Pillars of Context

| Pillar | Content |
|--------|---------|
| **Identity** | User name, preferences, communication style |
| **Environment** | Current date, time, location |
| **Working Memory** | Active content (email, webpage) |
| **Artifacts** | Todo list, calendar events |

### 3-Tier Memory

| Tier | Scope | Example |
|------|-------|---------|
| **Short-term** | Current session | "user is tired", "use bullets" |
| **Long-term** | Permanent | Name, birthday, preferences |
| **Project** | Until completed | Goals, requirements, progress |

## Available Tools

| Category | Tools |
|----------|-------|
| **Memory** | save/query short/long/project memory, search, recall |
| **Gmail** | check_gmail_and_learn, send email |
| **Calendar** | get/create/update/delete events |
| **Web** | read_web_page, watch_youtube |
| **Tasks** | add/get/complete todo |

## Environment

```bash
# .env
GEMINI_API_KEY=your_key
GOOGLE_CLIENT_ID=your_oauth_client_id
GOOGLE_CLIENT_SECRET=your_oauth_secret
```

## Data Storage

- **ChromaDB**: `emo_memory/` - Vector embeddings for semantic search
- **JSON**: `user_config.json`, `todo.json`, `chat_history.json`
- **OAuth**: `credentials/` - Google API tokens per service
