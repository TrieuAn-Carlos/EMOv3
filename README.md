# EMO - Helping students --like-- love maths.

AI assistant with Gmail/Calendar integration, persistent memory, and multi-tier context.

## Tech Stack

- **Backend**: FastAPI + LangGraph
- **Frontend**: Next.js + React
- **AI**: Google Gemini 2.5 Flash (optionally Groq)
- **Memory**: ChromaDB (vector DB)
- **Integrations**: Gmail API, Google Calendar API, YouTube Transcript API, Jina Reader

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py
# API runs at http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev
# UI runs at http://localhost:3000
```

## Project Structure

```
├── backend/              # FastAPI backend
│   ├── main.py          # FastAPI app entry
│   ├── agent/           # LangGraph agent + tools
│   ├── routers/         # API endpoints (chat, auth, email, calendar, tasks)
│   ├── integrations/    # External APIs (Gmail, Calendar, Web)
│   ├── memory/          # ChromaDB + 4-Pillar context
│   ├── services/        # Business logic
│   └── data/            # Runtime data (sessions, todos)
│
├── frontend/            # Next.js frontend
│   ├── src/
│   └── package.json
│
├── emo_memory/          # ChromaDB database
└── .env                 # API keys (GEMINI_API_KEY)
```

## Architecture

```
User → Next.js UI → FastAPI Backend → Gemini (with tools) → Response
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
