"""
Chat History Manager for AI Agent
Handles persistent storage of chat sessions in JSON format.
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini for title generation
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

HISTORY_FILE = Path(__file__).parent / "chat_history.json"


def load_all_sessions() -> Dict:
    """Load all chat sessions from JSON file."""
    if not HISTORY_FILE.exists():
        return {}
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_all_sessions(sessions: Dict) -> None:
    """Internal helper to save all sessions to JSON file."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def save_session(session_id: str, messages: List[Dict]) -> None:
    """Save or update a session's messages."""
    sessions = load_all_sessions()
    
    if session_id in sessions:
        sessions[session_id]["messages"] = messages
    else:
        sessions[session_id] = {
            "title": "New Chat",
            "created_at": datetime.now().isoformat(),
            "messages": messages
        }
    
    _save_all_sessions(sessions)


def create_new_session() -> str:
    """Create a new empty session and return its ID."""
    sessions = load_all_sessions()
    session_id = str(uuid.uuid4())
    
    sessions[session_id] = {
        "title": "New Chat",
        "created_at": datetime.now().isoformat(),
        "messages": []
    }
    
    _save_all_sessions(sessions)
    return session_id


def generate_title(session_id: str, first_message: str) -> str:
    """Generate a smart title using AI from the first message."""
    sessions = load_all_sessions()
    
    # Default fallback title
    fallback_title = first_message.strip()[:27] + "..." if len(first_message.strip()) > 30 else first_message.strip()
    if not fallback_title:
        fallback_title = "New Chat"
    
    title = fallback_title
    
    # Try to generate title with AI
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"""Generate a very short title (maximum 5 words) for a conversation that starts with this message. 
Return ONLY the title, nothing else. No quotes, no explanation.

User's first message: "{first_message}"

Title:"""
            
            response = model.generate_content(prompt)
            ai_title = response.text.strip().strip('"\'')
            
            # Validate and use AI title
            if ai_title and len(ai_title) <= 50:
                title = ai_title[:30] if len(ai_title) > 30 else ai_title
        except Exception:
            # Fallback to truncated message on any error
            pass
    
    if session_id in sessions:
        sessions[session_id]["title"] = title
        _save_all_sessions(sessions)
    
    return title


def delete_session(session_id: str) -> bool:
    """Delete a specific session. Returns True if successful."""
    sessions = load_all_sessions()
    
    if session_id in sessions:
        del sessions[session_id]
        _save_all_sessions(sessions)
        return True
    
    return False


def get_session_messages(session_id: str) -> Optional[List[Dict]]:
    """Get messages for a specific session."""
    sessions = load_all_sessions()
    
    if session_id in sessions:
        return sessions[session_id].get("messages", [])
    
    return None


def get_sessions_sorted() -> List[tuple]:
    """Get all sessions sorted by created_at (newest first)."""
    sessions = load_all_sessions()
    
    sorted_sessions = sorted(
        sessions.items(),
        key=lambda x: x[1].get("created_at", ""),
        reverse=True
    )
    
    return sorted_sessions
