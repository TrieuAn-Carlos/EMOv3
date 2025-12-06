# EMO - Project Overview

Personal AI assistant with conversation, email, memory, quizzes, and web tools.

## What It Does

- Chat with AI (Groq LLM)
- Manage Gmail (search, attachments)
- Smart memory (vector database)
- Interactive quizzes (auto-grading with LaTeX)
- Task management (todos with reminders)
- Web tools (YouTube, web pages, news)

## How It Works

### Architecture Overview

The system follows a 3-phase pipeline:

1. **Classify** - Fast keyword matching detects query type (no AI needed)
   - "email" → triggers email tools
   - "quiz" → generates quiz
   - "remember" → accesses memory
   - Instant, no API calls

2. **Execute** - Runs appropriate tools based on classification
   - Email search and extraction
   - Web page fetching
   - Memory recall from ChromaDB
   - Collects all results for context

3. **Generate** - Single Groq API call with full context
   - System prompt (identity + environment)
   - Recent conversation history (last 6 messages)
   - Tool execution results
   - User message
   - Streams response word-by-word for real-time feel

### Context Pillars (4 Layers)

Every AI request includes all context:

1. **Identity** - User's name, communication style, preferences (from `user_config.json`)
2. **Environment** - Current date, time, timezone, location
3. **Working Memory** - Active content (email being read, webpage viewed)
4. **Artifacts** - Todos, calendar events, saved data

Plus: Long-term facts stored in ChromaDB vector database

## Core Features Explained

### Chat with AI

- Incoming message triggers memory recall
- System queries ChromaDB for relevant past memories
- Builds full context with identity + time + memory
- Sends to Groq LLM
- Streams response to UI
- Saves message to chat history

### Gmail Integration

- OAuth 2.0 authentication (first login only)
- Searches emails by keyword
- Extracts attachments (PDF, Word documents)
- Auto-learns important information (saves to memory)
- Read-only access (safe)

### Smart Memory System

Uses ChromaDB (vector database) for semantic search with 3 tiers:

- **Short-term**: Temporary, cleared on session end
- **Long-term**: Persistent facts about user
- **Project**: Project-specific memories

Automatically triggered when relevant keywords detected in conversation.

### Interactive Quizzes

Process: AI generates JSON → Parse JSON → Render quiz → Auto-grade answers

Features:
- 2 question types (both auto-gradable):
  - Multiple choice (4 options, user clicks one)
  - True/False (user clicks True or False)
- LaTeX support for math equations: `$x^2 + y^2 = r^2$`, `$\frac{d}{dx}x^2 = 2x$`
- Uses Streamlit fragments (`@st.fragment`) for smooth UI (only quiz rerenders, not whole page)
- Immediate grading upon submit
- Shows explanations for each question

### Todo Manager

- Add tasks with optional deadlines
- Automatic reminders based on time until deadline
- Complete/mark tasks as done
- View all active tasks
- Stored in `todo.json`

### Web Tools

- **YouTube**: Fetches full transcript with timestamps
- **Web Pages**: Reads and extracts clean text via Jina API
- **News**: Gets latest headlines

## Project Structure

```
main.py              Main application (4800+ lines)
├── Rendering (LaTeX, streaming, special formatting)
├── Gmail auth & tools
├── Memory management (ChromaDB)
├── Quiz generator (JSON parsing + UI)
├── Todo system
├── Web scraping (YouTube, web, news)
├── Groq API integration
└── Universal context system

tools.py             All tool implementations
state.py             Context management (4 Pillars)
history.py           Chat session management
agent.py             LangGraph agent (experimental)

user_config.json     Your identity & preferences
todo.json            Tasks list
chat_history.json    All past conversations
emo_memory/          ChromaDB vector database
├── chroma.sqlite3   Database file
└── [collections]    Stored memories

credentials.json     Google OAuth credentials
token.json           Gmail API token (auto-generated)
.env                 API keys (GROQ_API_KEY, etc)
```

## Authentication & Security

### Gmail

- Uses Google OAuth 2.0 (official Google login)
- First login: Browser opens, you authorize
- Token saved to `token.json` for future sessions (auto-refresh)
- Only read-only access (can't delete/modify emails)

### Groq API

- API key stored in `.env` file
- Never committed to git (in `.gitignore`)
- Used for LLM processing

## Data Storage

| File | Purpose | Format |
|------|---------|--------|
| `user_config.json` | Your name, style, role | JSON |
| `todo.json` | Tasks with deadlines | JSON |
| `chat_history.json` | All chat sessions | JSON |
| `emo_memory/` | Vector embeddings (memories) | ChromaDB |
| `.env` | Sensitive API keys | Key=Value |

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **UI** | Streamlit | Fast Python web apps, great for chat |
| **LLM** | Groq API (Meta Llama models) | Fast inference, open-source, affordable |
| **Memory** | ChromaDB | Vector database, semantic search, local, fast |
| **Email** | Gmail API | Official Google API, secure |
| **Web** | Jina API | Clean text extraction from websites |
| **Video** | YouTube Transcript API | Official transcripts with timestamps |
| **Rendering** | Markdown + LaTeX | Beautiful text and math formulas |

## Session State

Streamlit session state manages:

- `current_session_id` - Active chat ID
- `messages` - Chat history for current session
- `active_quizzes` - Currently active quizzes
- `quiz_data_store` - Quiz backup storage
- `available_tools` - Tools dictionary
- `gmail_authenticated` - Gmail login status
- `show_thinking` - Toggle for AI reasoning display

## Design Philosophy

**"Context is King"** - Every decision informed by:
- **Who you are** (identity from user_config)
- **When it is** (current time/date/timezone)
- **What you know** (long-term and short-term memories)
- **What you're doing** (working memory)
- **What matters** (todos and deadlines)

This makes the AI feel personal and contextual, not generic.

## Why This Architecture?

### 3-Phase Design Benefits

- **Fast**: One API call, not multiple (pre-classified tools)
- **Reliable**: No tool hallucination (explicit tool selection)
- **Controllable**: You decide which tools run (not AI)
- **Efficient**: Pre-filtered context reduces token usage

### Fragment-Based Quiz UI

- Smooth interaction (only quiz updates, not whole page)
- No jarring reloads when answering questions
- Better user experience than full page rerun

### Vector Database for Memory

- Semantic search (finds relevant memories even with different wording)
- Fast queries (local ChromaDB)
- Scalable (handles hundreds of memories)

## Current Capabilities

Working:
- Multi-turn chat with memory
- Gmail search & fetch with attachments
- Todo management with reminders
- Quiz generation (multiple choice + true/false)
- LaTeX rendering in quizzes and messages
- YouTube transcript fetching
- Web page reading
- Session persistence

## Future Possibilities

- Voice input/output
- Image analysis and generation
- Calendar integration
- Email composition & sending
- File upload and analysis
- Advanced memory search UI
