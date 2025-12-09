# 🏗️ EMO Technical Overview for SocratiQ Architecture

Technical analysis for planning "Adaptive AI & PDF Learning" feature upgrade.

---

## 📊 1. Database Schema

> **Note:** This project uses **Python/SQLAlchemy** (not Prisma). Database is SQLite.

### File: `backend/database.py`

```python
class ChatSession(Base):
    """Model cho chat session"""
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True)
    title = Column(String, default="Cuộc trò chuyện mới")
    title_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    message_count = Column(Integer, default=0)
    
    # Relationship với messages
    messages = relationship("Message", back_populates="session", 
                          cascade="all, delete-orphan", 
                          order_by="Message.timestamp")


class Message(Base):
    """Model cho individual message"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
```

### Database Location

```
backend/data/sessions.db  (SQLite)
```

### Missing Models for SocratiQ

- ❌ `User` - No user authentication
- ❌ `Document` - No PDF/file storage
- ❌ `Quiz` - No quiz persistence
- ❌ `LearningProgress` - No adaptive tracking

---

## 🤖 2. Current AI Logic

### Main Chat Router: `backend/routers/chat.py`

**Key Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/` | POST | Non-streaming chat |
| `/api/chat/stream` | GET (SSE) | **Streaming chat** (main endpoint) |
| `/api/chat/sessions` | GET/POST | Session CRUD |
| `/api/chat/sessions/{id}` | GET/DELETE | Session detail/delete |

**Streaming Handler:**

```python
@router.get("/stream")
async def chat_stream(message: str, session_id: Optional[str] = None):
    async def generate():
        # Auto-create session if not provided
        if not session_id:
            new_session = service.create_session()
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': new_session.id})}\n\n"
        
        # Stream response from Gemma
        async for chunk in stream_chat_with_gemma(message, session_id, db):
            yield f"data: {json.dumps(chunk)}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Agent Implementation: `backend/agent/agent.py`

**Architecture:** LangGraph ReAct Agent

```python
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# Model Configuration
_llm = ChatGoogleGenerativeAI(
    model="gemma-3-27b-it",  # Gemma 3 27B
    api_key=GEMINI_API_KEY,
    temperature=TEMPERATURE,
    max_tokens=MAX_OUTPUT_TOKENS,
)

# Create Agent with Tools
_agent = create_react_agent(
    _llm,
    tools,  # from agent/tools.py
    prompt=build_system_prompt(_context_state),
)
```

**Key Features:**

- ✅ Session history from SQLite
- ✅ Memory query from ChromaDB
- ✅ Tool calls (Gmail, Calendar, Web, Tasks)
- ✅ Streaming via SSE

### Tools Available: `backend/agent/tools.py`

- `search_gmail` - Search email
- `get_email` - Get full email content
- `analyze_email_attachment` - Parse attachments
- `get_calendar_events` - List events
- `add_calendar_event` - Create events
- `add_task` / `list_tasks` / `complete_task`
- `read_webpage` - Fetch web content
- `get_youtube_transcript` - YouTube transcripts
- `get_news` - News headlines
- `remember_fact` / `recall_personal_info` - Memory

---

## 📁 3. File/PDF Handling

### Current State: ⚠️ **Partial Support**

| Feature | Status | Notes |
|---------|--------|-------|
| Upload Route | ❌ None | No `/api/upload` endpoint |
| PDF Parsing | 🟡 Library only | `pypdf>=4.0.0` in requirements |
| Text Extraction | 🟡 Email attachments only | `analyze_email_attachment` tool |
| File Storage | ❌ None | No file storage system |
| ChromaDB | ✅ Exists | For memory, not documents |

### Attachment Parsing (Gmail only)

```python
# In integrations/gmail.py
def analyze_attachment(email_index: int, attachment_index: int = 1):
    # Downloads attachment from Gmail API
    # Parses with pypdf/docx/pandas based on file type
    # Returns extracted text
```

### Missing for SocratiQ

1. **Upload endpoint** - Accept PDF/files from frontend
2. **Document storage** - Save files to disk/cloud
3. **Text chunking** - Split PDFs for embedding
4. **Vector embedding** - Store in ChromaDB for RAG
5. **Document model** - Track uploaded files in DB

---

## 📦 4. Dependencies

### Backend (`backend/requirements.txt`)

| Category | Package | Version | Purpose |
|----------|---------|---------|---------|
| **Framework** | fastapi | ≥0.104.0 | Web framework |
| | uvicorn | ≥0.24.0 | ASGI server |
| | pydantic | ≥2.0.0 | Validation |
| | sqlalchemy | ≥2.0.0 | ORM |
| **AI** | langchain-core | ≥0.3.0 | LLM orchestration |
| | langchain-google-genai | ≥2.0.0 | Gemini integration |
| | langgraph | ≥0.2.0 | Agent framework |
| | openai | ≥1.0.0 | OpenAI client |
| **Vector DB** | chromadb | ≥0.5.0 | Memory storage |
| **Document** | pypdf | ≥4.0.0 | PDF parsing |
| | python-docx | ≥1.0.0 | Word docs |
| | pandas | ≥2.0.0 | CSV/Excel |
| | openpyxl | ≥3.1.0 | Excel support |
| **APIs** | google-api-python-client | ≥2.100.0 | Gmail/Calendar |

### Frontend (`frontend/package.json`)

| Category | Package | Version | Purpose |
|----------|---------|---------|---------|
| **Framework** | next | 16.0.7 | React framework |
| | react | 19.2.0 | UI library |
| **AI/Streaming** | ai | ^5.0.108 | Vercel AI SDK |
| **UI** | tailwindcss | ^4 | Styling |
| | lucide-react | ^0.556.0 | Icons |
| | zustand | ^5.0.9 | State management |
| **Content** | react-markdown | ^10.1.0 | Markdown rendering |
| | katex | ^0.16.27 | Math formulas |
| | rehype-katex | ^7.0.1 | KaTeX integration |

### Missing for SocratiQ

- ❌ `react-pdf` / `pdf.js` - PDF viewer in frontend
- ❌ `multer` or similar - File upload handling
- ❌ `sentence-transformers` - Better embeddings
- ⚠️ Frontend has `ai` SDK but backend uses custom SSE

---

## 🗂️ Project Structure

```
EMO/
├── backend/
│   ├── agent/
│   │   ├── agent.py          # LangGraph ReAct agent
│   │   ├── tools.py          # Tool definitions
│   │   └── gemma_function_calling.py  # Gemma wrapper
│   ├── core/
│   │   ├── config.py         # API keys, settings
│   │   └── state.py          # Context state
│   ├── integrations/
│   │   ├── gmail.py          # Gmail API
│   │   ├── calendar.py       # Calendar API
│   │   └── web.py            # Web scraping
│   ├── memory/
│   │   ├── chroma_memory.py  # ChromaDB wrapper
│   │   └── memory_tools.py   # Memory tools
│   ├── routers/
│   │   ├── chat.py           # Chat API
│   │   ├── auth.py           # OAuth
│   │   ├── email.py          # Direct email API
│   │   └── calendar.py       # Calendar API
│   ├── services/
│   │   ├── session_service.py
│   │   └── task_service.py
│   ├── database.py           # SQLAlchemy models
│   ├── main.py               # FastAPI app
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── [[...sessionId]]/page.tsx  # Main page
│   │   ├── components/
│   │   │   └── chat/
│   │   │       ├── ChatContainer.tsx
│   │   │       └── Message.tsx
│   │   └── store/
│   │       └── useAppStore.ts
│   └── package.json
```

---

## 🎯 SocratiQ Implementation Gaps

### Must Add

1. **User Authentication** - User model + auth flow
2. **Document Upload API** - `POST /api/documents/upload`
3. **Document Model** - SQLAlchemy model for files
4. **PDF Processing Pipeline** - Extract → Chunk → Embed
5. **RAG Integration** - Query docs in agent context
6. **Quiz Generation** - Tool + persistence
7. **Learning Progress Tracking** - Adaptive algorithm

### Can Reuse

- ✅ ChromaDB infrastructure (extend for documents)
- ✅ LangGraph agent (add document tools)
- ✅ SSE streaming (no changes needed)
- ✅ Session management (extend for quizzes)

---

*Generated for SocratiQ architecture planning - December 2025*
