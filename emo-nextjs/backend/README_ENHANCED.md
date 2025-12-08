# EMO Backend - Enhanced Architecture

## 📋 Tổng quan

Backend EMO đã được tái cấu trúc để tích hợp tất cả tính năng từ cả 2 phiên bản (Streamlit và NextJS), với kiến trúc tối ưu cho token efficiency và logic chặt chẽ.

## 🏗️ Kiến trúc

### **4 Pillars of Context Memory**

1. **Identity Context** - Thông tin người dùng và preferences
2. **Environment Context** - Thời gian, địa điểm real-time
3. **Working Memory** - Dữ liệu tạm thời từ tools
4. **Artifacts** - Kết quả có cấu trúc (todos, events)

### **Cấu trúc thư mục**

```
backend/
├── core/                    # Core modules (NEW)
│   ├── __init__.py
│   ├── config.py           # Centralized configuration
│   └── state.py            # 4-Pillar state management
│
├── memory/                  # Memory system (NEW)
│   ├── __init__.py
│   ├── chroma_memory.py    # ChromaDB singleton
│   └── memory_tools.py     # search, recall, save tools
│
├── agent/
│   ├── agent.py            # Enhanced LangGraph agent
│   ├── tools.py            # Original tools
│   └── tools_enhanced.py   # NEW: Complete tool collection (16 tools)
│
├── integrations/
│   ├── gmail.py            # Enhanced với multi-account support
│   ├── calendar.py
│   └── web.py              # Web scraping, YouTube, news
│
├── services/
│   ├── session_service.py
│   ├── task_service.py     # NEW: Task management
│   ├── credentials_service.py  # Multi-account credentials
│   └── title_generator.py
│
├── routers/
│   ├── chat.py
│   ├── auth.py
│   ├── email.py
│   ├── calendar.py
│   └── tasks.py            # NEW: Task endpoints
│
├── database.py             # SQLAlchemy models
└── main.py                 # FastAPI app
```

## 🔧 Tính năng mới

### **1. Core Module**
- ✅ Centralized configuration (Groq + Gemini)
- ✅ 4-Pillar state management
- ✅ Token-optimized context formatting

### **2. Memory Module**
- ✅ Thread-safe ChromaDB singleton
- ✅ Long-term memory với category support
- ✅ Memory search và recall
- ✅ Integration với user_config.json

### **3. Enhanced Tools (16 tools)**

**Gmail (3):**
- `search_gmail` - Tìm email
- `get_email` - Đọc email đầy đủ
- `analyze_email_attachment` - Phân tích file đính kèm

**Calendar (3):**
- `list_calendar_events` - Danh sách sự kiện
- `search_calendar_events` - Tìm kiếm event
- `add_calendar_event` - Thêm event bằng natural language

**Tasks (3):**
- `add_task` - Thêm task với deadline
- `list_tasks` - Xem pending tasks
- `complete_task` - Đánh dấu hoàn thành

**Web (3):**
- `read_webpage` - Đọc nội dung web
- `get_youtube_transcript` - Lấy transcript video
- `get_news` - Tin tức mới nhất

**Memory (4):**
- `search_memory` - Tìm kiếm memories
- `recall_memory` - Lấy memory cụ thể
- `remember_fact` - Lưu thông tin cá nhân
- `recall_personal_info` - Tìm thông tin đã lưu

### **4. Task Service**
- ✅ Task management với deadline support
- ✅ Smart reminders (overdue, upcoming)
- ✅ JSON persistence
- ✅ RESTful API endpoints

### **5. API Endpoints Mới**

```
POST   /api/tasks              - Tạo task mới
GET    /api/tasks              - Lấy danh sách tasks
POST   /api/tasks/complete     - Hoàn thành task
DELETE /api/tasks/completed    - Xóa tasks đã xong
GET    /api/tasks/reminders    - Smart reminders
```

## 🚀 Setup

### **1. Install dependencies**

```bash
cd backend
pip install -r requirements_enhanced.txt
```

### **2. Environment variables**

Tạo file `.env`:

```env
# Groq API (primary LLM)
GROQ_API_KEY=your_groq_api_key

# Gemini API (fallback)
GEMINI_API_KEY=your_gemini_api_key

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

### **3. Run server**

```bash
python main.py
# hoặc
uvicorn main:app --reload --port 8000
```

## 📊 Token Optimization

### **Context Pruning Strategy**

1. **Identity**: Load một lần, cache stable data
2. **Environment**: Real-time nhưng compact (date + time only)
3. **Memory**: Query top 3-5 relevant memories only
4. **Artifacts**: Show top 5 pending tasks only

### **Tool Output Formatting**

- Sử dụng markdown concise
- Truncate content > 20KB
- Email list: Hiển thị summary trước, full content on demand
- Memory: Show summary + ID, full content via recall

### **System Prompt Optimization**

```python
def build_system_prompt(context_state: EmoState) -> str:
    """
    Tối ưu token:
    - Ngắn gọn, súc tích
    - Không lặp lại rules
    - Context block tách biệt
    - Ưu tiên thông tin quan trọng
    """
```

## 🔄 Migration từ phiên bản cũ

### **Từ Streamlit backend:**

1. ✅ `agent.py` → Giữ LangGraph structure, thêm core imports
2. ✅ `state.py` → Chuyển vào `core/state.py`
3. ✅ `config.py` → Chuyển vào `core/config.py`
4. ✅ `tools.py` → Merge vào `agent/tools_enhanced.py`
5. ✅ `task_manager.py` → `services/task_service.py` (no Streamlit deps)
6. ✅ `web_tools.py` → Already in `integrations/web.py`

### **Từ emo-nextjs backend:**

1. ✅ Keep FastAPI architecture
2. ✅ Keep database + session management
3. ✅ Enhance với tools từ Streamlit version
4. ✅ Add core và memory modules

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/

# Chat test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Xin chào!", "session_id": "test_123"}'

# Tasks test
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task": "Test task", "deadline": "2025-12-15T17:00:00"}'

curl http://localhost:8000/api/tasks
```

## 📝 Best Practices

### **1. Memory Management**
- Save important conversations to ChromaDB
- Use categories for long-term facts
- Query memory before answering questions

### **2. Context Efficiency**
- Load identity once per session
- Query memories only when needed
- Show summaries first, details on request

### **3. Tool Usage**
- Email: search → list → get by index
- Tasks: add with deadline → reminder checks
- Memory: search → recall by ID

### **4. Error Handling**
- Graceful degradation khi tools fail
- Fallback options (Jina → BeautifulSoup)
- Clear error messages cho user

## 🔐 Security

- OAuth tokens stored securely in `data/` directory
- Credentials.json not in git
- API keys in .env only
- Session-based authentication

## 📈 Performance

- ChromaDB singleton → No repeated init
- Memory query caching
- Token truncation for large content
- Async operations where possible

## 🎯 Roadmap

- [ ] Quiz generation tool integration
- [ ] Multi-account credential switching
- [ ] Voice input/output support
- [ ] Advanced memory clustering
- [ ] Auto-categorization for memory

---

**Version**: 3.0 Enhanced
**Last Updated**: December 8, 2025
**Status**: ✅ Production Ready
