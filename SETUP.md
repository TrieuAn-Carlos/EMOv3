# EMO Development Setup Guide

Complete step-by-step instructions for running EMO on your local machine.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** and **npm** ([Download](https://nodejs.org/))
- **Git** ([Download](https://git-scm.com/))
- **Google Cloud Project** with APIs enabled (for Gmail/Calendar integration)

### System Requirements
- macOS, Linux, or Windows
- At least 4GB RAM (8GB recommended)
- 2GB free disk space

---

## 🚀 Quick Start (TL;DR)

```bash
# 1. Backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your API keys
python main.py

# 2. Frontend (in new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser!

---

## 📦 Step-by-Step Installation

### Step 1: Clone the Repository

```bash
cd ~/Projects
git clone <your-repo-url>
cd EMOv3
```

### Step 2: Backend Setup

#### 2.1 Create Python Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

> **Tip:** You should see `(venv)` in your terminal prompt when activated.

#### 2.2 Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- **FastAPI** - Backend framework
- **LangChain & LangGraph** - AI orchestration
- **ChromaDB** - Vector database for memory
- **Google API clients** - Gmail & Calendar integration
- **SQLAlchemy** - Database ORM

#### 2.3 Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
touch .env
```

Add the following configuration:

```env
# Required: Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Google OAuth (for Gmail/Calendar)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Optional: Database (defaults to SQLite)
DATABASE_URL=sqlite:///data/sessions.db
```

**How to get API keys:**

1. **Gemini API Key** (Required):
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Click "Get API Key" → "Create API key"
   - Copy and paste into `.env`

2. **Google OAuth Credentials** (Optional - for Gmail/Calendar):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable **Gmail API** and **Google Calendar API**
   - Go to **Credentials** → **Create Credentials** → **OAuth client ID**
   - Choose **Desktop app**
   - Download credentials and copy Client ID & Secret to `.env`

#### 2.4 Initialize Database

The database will be automatically created on first run, but you can verify setup:

```bash
python -c "from database import init_db; init_db()"
```

You should see: `✅ Database initialized at: backend/data/sessions.db`

### Step 3: Frontend Setup

#### 3.1 Install Node Dependencies

```bash
cd ../frontend  # From project root
npm install
```

This installs:
- **Next.js 16** - React framework
- **TailwindCSS 4** - Styling
- **Lucide React** - Icons
- **React Markdown** - Message rendering
- **Zustand** - State management

#### 3.2 Configure Frontend (Optional)

The frontend is pre-configured to connect to `http://localhost:8000`. If you need to change the backend URL, create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## ▶️ Running the Application

### Terminal 1: Start Backend

```bash
cd backend
source venv/bin/activate  # Activate virtual environment
python main.py
```

**Expected output:**
```
🚀 EMO Backend starting...
✅ Database initialized at: backend/data/sessions.db
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Backend API is now running at: **http://localhost:8000**

### Terminal 2: Start Frontend

```bash
cd frontend
npm run dev
```

**Expected output:**
```
   ▲ Next.js 16.0.7
   - Local:        http://localhost:3000
   - Network:      http://192.168.1.x:3000

 ✓ Starting...
 ✓ Ready in 2.3s
```

Frontend UI is now running at: **http://localhost:3000**

---

## ✅ Verify Installation

### 1. Check Backend Health

Visit: http://localhost:8000/api/health

Expected response:
```json
{
  "status": "healthy",
  "gemini_configured": true
}
```

### 2. Check Frontend

Open: http://localhost:3000

You should see:
- EMO chat interface
- Collapsible sidebar with "New Chat" button
- Welcome message: "Xin chào! Mình là Emo"
- Suggestion pills (Tasks, Email, Quiz, News)

### 3. Test a Message

Type: **"Hello!"**

You should receive a streaming response from the AI assistant.

---

## 🗂️ Project Structure After Setup

```
EMOv3/
├── backend/
│   ├── venv/                    # Python virtual environment (created)
│   ├── data/
│   │   ├── sessions.db          # SQLite database (auto-created)
│   │   ├── emo_memory/          # ChromaDB vector store (auto-created)
│   │   ├── gmail_token.json     # Google OAuth tokens (optional)
│   │   └── calendar_token.json  # Google OAuth tokens (optional)
│   ├── .env                     # Environment variables (you created)
│   ├── requirements.txt
│   └── main.py
│
├── frontend/
│   ├── node_modules/            # Node dependencies (created)
│   ├── .next/                   # Next.js build cache (auto-created)
│   ├── package.json
│   └── src/
│
└── emo_memory/                  # Legacy ChromaDB (may exist)
```

---

## 🔧 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'fastapi'`

**Solution:** Activate virtual environment and reinstall:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: `Error: Cannot find module 'next'`

**Solution:** Reinstall frontend dependencies:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: `GEMINI_API_KEY not configured`

**Solution:** Add API key to `backend/.env`:
```env
GEMINI_API_KEY=AIza...your_key_here
```

Then restart backend server.

### Issue: `Port 3000 already in use`

**Solution:** Kill existing process or use different port:
```bash
# Option 1: Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Option 2: Use different port
PORT=3001 npm run dev
```

### Issue: `CORS errors` in browser console

**Solution:** Verify:
1. Backend is running on port 8000
2. Frontend is running on port 3000
3. Check `backend/main.py` CORS settings include `http://localhost:3000`

### Issue: Gmail/Calendar integration not working

**Solution:** 
1. Verify Google OAuth credentials in `.env`
2. Enable Gmail API and Calendar API in Google Cloud Console
3. First-time authorization will open browser for OAuth flow
4. Tokens will be saved to `backend/data/gmail_token.json`

---

## 🔄 Development Workflow

### Making Backend Changes

Backend has **hot reload** enabled:
```bash
# Edit any .py file
# Server automatically restarts
# Watch terminal for errors
```

### Making Frontend Changes

Frontend has **Fast Refresh**:
```bash
# Edit any .tsx file
# Browser automatically updates
# No manual refresh needed
```

### Database Management

View database contents:
```bash
cd backend/data
sqlite3 sessions.db
sqlite> SELECT * FROM chat_sessions;
sqlite> .quit
```

Clear all sessions:
```bash
rm backend/data/sessions.db
# Will be recreated on next backend start
```

---

## 📊 API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Available endpoints:
- `POST /api/chat/` - Send message (non-streaming)
- `GET /api/chat/stream` - Send message (streaming)
- `GET /api/chat/sessions` - List all sessions
- `POST /api/chat/sessions` - Create new session
- `DELETE /api/chat/sessions/{id}` - Delete session
- `GET /api/emails/list` - Direct email fetch
- `GET /api/calendar/events` - List calendar events

---

## 🧪 Testing

### Test Backend Only

```bash
cd backend
source venv/bin/activate
python -c "from main import app; print('✅ Backend imports successful')"
```

### Test Frontend Only

```bash
cd frontend
npm run build
# Should complete without errors
```

### Test API Endpoint

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test chat endpoint (requires backend running)
curl -X GET "http://localhost:8000/api/chat/stream?message=hello"
```

---

## 🛑 Stopping the Application

### Stop Backend
In backend terminal: Press `Ctrl+C`

### Stop Frontend
In frontend terminal: Press `Ctrl+C`

### Deactivate Python Virtual Environment
```bash
deactivate
```

---

## 🔐 Security Notes

> **⚠️ Important:** Never commit `.env` file to Git

Add to `.gitignore` (should already be included):
```gitignore
# Environment variables
.env
.env.local

# API tokens
backend/data/*_token.json
backend/data/credentials.json
```

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Gemini API Reference](https://ai.google.dev/docs)
- [ChromaDB Documentation](https://docs.trychroma.com/)

---

## 🆘 Need Help?

If you encounter issues:
1. Check logs in terminal
2. Verify all prerequisites are installed
3. Ensure `.env` file is configured correctly
4. Try deleting `venv/` and `node_modules/` and reinstalling
5. Check that ports 3000 and 8000 are available

---

**Happy coding! 🎉**
