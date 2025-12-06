# EMO - AI Email Assistant

A personal AI assistant with Gmail integration, persistent memory, and multi-tier context management.

---

## Tech Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| **Frontend** | Streamlit | Web UI, chat interface |
| **AI Model** | Google Gemini 2.5 Flash | Main LLM for conversations |
| **Vector DB** | ChromaDB | Semantic search & memory storage |
| **Email** | Gmail API | Read, search, send emails |
| **Auth** | Google OAuth 2.0 | Gmail authentication |
| **Web Scraping** | BeautifulSoup, Jina API | Read web pages |
| **Video** | YouTube Transcript API | Fetch video transcripts |

---

## Project Structure

```
EMO/
├── main.py              # Main app - Streamlit UI + Gemini integration
├── tools.py             # All AI tools (memory, web, youtube, etc.)
├── state.py             # Universal Context (4 Pillars architecture)
├── history.py           # Chat session management
├── agent.py             # LangGraph agent (experimental)
│
├── user_config.json     # User identity + long-term facts
├── todo.json            # Task list storage
├── chat_history.json    # All chat sessions
│
├── credentials.json     # Google OAuth credentials (from GCP)
├── token.json           # Gmail access token (auto-generated)
├── .env                 # API keys (GEMINI_API_KEY)
│
├── emo_memory/          # ChromaDB vector database
│   ├── chroma.sqlite3   # Main database file
│   └── [uuid folders]/  # Collection data
│
├── requirements.txt     # Python dependencies
└── venv/                # Virtual environment
```

---

## How It Works

### 1. The Flow

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  1. MEMORY RECALL                                       │
│     Query ChromaDB for relevant past memories           │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  2. CONTEXT INJECTION                                   │
│     Add: Identity + Time + Long-term facts + Memories   │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  3. GEMINI PROCESSING                                   │
│     LLM decides: respond directly OR use tools          │
└─────────────────────────────────────────────────────────┘
     │
     ├── Tool needed? ──► Execute tool ──► Return result ──┐
     │                                                      │
     ▼                                                      │
┌─────────────────────────────────────────────────────────┐
│  4. RESPONSE                                            │◄─┘
│     Stream response to user                             │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  5. SAVE                                                │
│     Save chat to history, update memories if needed     │
└─────────────────────────────────────────────────────────┘
```

### 2. The 4 Pillars of Context (state.py)

Every request includes:

| Pillar | Content | Source |
|--------|---------|--------|
| **Identity** | Name, role, communication style | `user_config.json` |
| **Environment** | Current date, time, location | System clock |
| **Working Memory** | Active content (email, webpage) | Tools output |
| **Artifacts** | Todo list, calendar events | `todo.json` |

Plus: **Long-term facts** (permanent memories about user)

### 3. The 3-Tier Memory System (tools.py)

```
┌─────────────────────────────────────────────────────────┐
│                    MEMORY TIERS                          │
├─────────────────┬─────────────────┬─────────────────────┤
│  SHORT-TERM     │  LONG-TERM      │  PROJECT            │
│  (Session)      │  (Permanent)    │  (Task-based)       │
├─────────────────┼─────────────────┼─────────────────────┤
│ Scoped to chat  │ Never expires   │ Until completed     │
│ session only    │ unless changed  │                     │
│                 │                 │                     │
│ Examples:       │ Examples:       │ Examples:           │
│ • "user tired"  │ • Name, age     │ • Project goals     │
│ • "use bullets" │ • Birthday      │ • Requirements      │
│ • "coding now"  │ • Preferences   │ • Progress notes    │
└─────────────────┴─────────────────┴─────────────────────┘

Storage: ChromaDB collections
- short_term_memory (filtered by session_id)
- long_term_memory
- project_memory
```

---

## Available Tools

### Memory Tools
| Tool | Purpose |
|------|---------|
| `save_short_term_memory` | Save session-specific context |
| `save_long_term_memory` | Save permanent facts about user |
| `save_project_memory` | Save project info (goals, progress) |
| `query_short_term` | Search current session memory |
| `query_long_term` | Search permanent facts |
| `query_project` | Search project information |
| `list_all_projects` | List active projects |
| `update_long_term_memory` | Correct/update permanent facts |
| `search_memory` | Search general memory (emails, etc.) |
| `recall_memory` | Get full content by ID |

### Gmail Tools
| Tool | Purpose |
|------|---------|
| `check_gmail_and_learn` | Search emails, extract content, save to memory |

### Productivity Tools
| Tool | Purpose |
|------|---------|
| `add_todo` | Add task to todo list |
| `get_todos` | Get pending tasks |
| `complete_todo` | Mark task as done |

### Web Tools
| Tool | Purpose |
|------|---------|
| `read_web_page` | Fetch and parse web content |
| `watch_youtube` | Get YouTube video transcript |
| `get_news_headlines` | Extract news from websites |

---

## APIs Used

### 1. Google Gemini API
- **Model**: `gemini-2.5-flash`
- **Purpose**: Main conversation AI with function calling
- **Auth**: API key in `.env` (`GEMINI_API_KEY`)

### 2. Gmail API
- **Scopes**: Read, send, modify emails
- **Auth**: OAuth 2.0 (`credentials.json` → `token.json`)
- **Setup**: Google Cloud Console project required

### 3. Jina Reader API
- **URL**: `https://r.jina.ai/{url}`
- **Purpose**: Convert web pages to clean markdown
- **Auth**: None (free tier)

### 4. YouTube Transcript API
- **Library**: `youtube_transcript_api`
- **Purpose**: Fetch video transcripts
- **Auth**: None

---

## Key Files Explained

### `main.py` (~2300 lines)
The main application file containing:
- Streamlit UI setup
- Chat interface
- Gmail integration (OAuth, search, send)
- Tool execution with real-time display
- Memory management (ChromaDB)
- Session management

### `tools.py` (~960 lines)
All AI-callable tools:
- 3-tier memory system (short/long/project)
- Web page reader
- YouTube transcript fetcher
- Memory search/recall

### `state.py` (~560 lines)
Universal Context architecture:
- TypedDict schemas for state
- Context initialization
- System prompt formatting
- Todo/artifact management

### `history.py` (~150 lines)
Chat session management:
- Create/load/save sessions
- Auto-generate titles with AI
- Sort sessions by date

---

## Data Flow Example

**User asks**: "What did John email me about the budget?"

```
1. Query ChromaDB → Find relevant email memories
2. Build context → Add user identity, time, memories
3. Send to Gemini → "User wants email info about budget from John"
4. Gemini calls → check_gmail_and_learn(query="from:john budget")
5. Tool executes → Search Gmail, extract content, save to memory
6. Gemini responds → "John sent you a budget report on Nov 15..."
7. Save to history → Store conversation in chat_history.json
```

---

## Running the App

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run Streamlit
streamlit run main.py

# 3. Open browser
# http://localhost:8501
```

---

## Environment Variables (.env)

```
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Database Schema

### ChromaDB Collections

| Collection | Purpose | Key Metadata |
|------------|---------|--------------|
| `emo_memory` | General memories (emails, web) | source, subject, date |
| `short_term_memory` | Session context | session_id, importance |
| `long_term_memory` | Permanent facts | category, permanent=True |
| `project_memory` | Project info | project_name, content_type |

### JSON Files

| File | Purpose | Structure |
|------|---------|-----------|
| `user_config.json` | User profile | name, preferences, long_term_facts |
| `todo.json` | Task list | [{id, task, status, created_at}] |
| `chat_history.json` | All sessions | {session_id: {title, messages}} |

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                         STREAMLIT UI                            │
│                        (main.py)                                │
└───────────────────────────┬────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  GEMINI 2.5     │ │   GMAIL API     │ │   CHROMADB      │
│  (AI Brain)     │ │   (Email)       │ │   (Memory)      │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         │    ┌──────────────┴───────────────┐   │
         │    │                              │   │
         ▼    ▼                              ▼   ▼
┌─────────────────────────────────────────────────────────────────┐
│                          TOOLS                                   │
│                        (tools.py)                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Memory  │ │  Web    │ │ YouTube │ │  Gmail  │ │  Todo   │   │
│  │ Tools   │ │ Reader  │ │ Trans.  │ │ Search  │ │ Manager │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UNIVERSAL CONTEXT                           │
│                        (state.py)                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Identity │ │   Env    │ │ Working  │ │Artifacts │           │
│  │          │ │          │ │ Memory   │ │          │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STORAGE                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ ChromaDB    │ │ JSON Files  │ │ OAuth Token │               │
│  │ (emo_memory)│ │ (config,    │ │ (token.json)│               │
│  │             │ │  history)   │ │             │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary

**EMO** is a personal AI assistant that:
1. **Remembers** you through 3-tier memory (short/long/project)
2. **Accesses** your Gmail to search and learn from emails
3. **Manages** your tasks and calendar
4. **Reads** web pages and YouTube videos
5. **Personalizes** responses based on your identity and preferences

Built with Streamlit + Gemini + ChromaDB + Gmail API.
