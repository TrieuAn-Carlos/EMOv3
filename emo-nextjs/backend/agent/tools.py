"""
EMO Backend - All Tools
=======================
All 16 tools migrated from Streamlit version.
No st.session_state - uses file/in-memory storage.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool

# =============================================================================
# CONFIGURATION
# =============================================================================

TODO_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "todo.json")
USER_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "user_config.json")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "emo_memory")

# Ensure data directory exists
os.makedirs(os.path.dirname(TODO_FILE), exist_ok=True)

# Email cache (in-memory)
_email_cache: list = []


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _load_json(filepath: str, default=None):
    """Load JSON file or return default."""
    if default is None:
        default = []
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
    except:
        pass
    return default


def _save_json(filepath: str, data):
    """Save data to JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# GMAIL TOOLS
# =============================================================================

@tool
def search_gmail(query: str, max_results: int = 5) -> str:
    """
    Search Gmail and get a list of recent emails.
    
    **AFTER CALLING THIS TOOL, YOU MUST:**
    1. Display the ENTIRE email list to the user
    2. Format: show all [1], [2], [3]... entries
    3. NEVER just ask "which email?" without showing the list
    
    Common queries:
    - "đọc mail" / "check email" → query="newer_than:7d"
    - "email from John" → query="from:John"
    - "email hôm nay" → query="newer_than:1d"
    
    Args:
        query: Gmail search query (e.g., "newer_than:7d", "from:john@example.com")
        max_results: Maximum emails to return (default 5)
    
    Returns:
        Numbered list: [1] Sender - Subject - Date (MUST show to user!)
    """
    global _email_cache
    try:
        from integrations.gmail import quick_gmail_search as _search
        result = _search(query, max_results)
        return result
    except ImportError:
        return "Gmail integration not available. Please connect Gmail first."
    except Exception as e:
        return f"Error searching Gmail: {str(e)[:100]}"


@tool
def get_email(index: int) -> str:
    """
    Fetch FULL email content by index number from the last search.
    
    **Use this AFTER search_gmail** to get the complete email body and attachments.
    
    Args:
        index: Email number from the search results (1, 2, 3, etc.)
    
    Returns:
        Full email with subject, sender, date, attachments list, and complete body text
    """
    try:
        from integrations.gmail import get_email_by_index as _get
        return _get(index)
    except ImportError:
        return "Gmail integration not available."
    except Exception as e:
        return f"Error getting email: {str(e)[:100]}"


@tool
def analyze_email_attachment(email_index: int, attachment_index: int = 1) -> str:
    """
    Read and analyze an attachment from an email.
    
    Args:
        email_index: Which email (1, 2, 3...)
        attachment_index: Which attachment (default 1)
    
    Returns:
        Extracted text content from the attachment
    """
    try:
        from integrations.gmail import analyze_attachment as _analyze
        return _analyze(email_index, attachment_index)
    except ImportError:
        return "Gmail integration not available."
    except Exception as e:
        return f"Error analyzing attachment: {str(e)[:100]}"


# =============================================================================
# TASK TOOLS
# =============================================================================

@tool
def add_task(task_description: str, deadline: str = None) -> str:
    """
    Add a new task to the todo list.
    
    Args:
        task_description: What needs to be done
        deadline: ISO datetime if task has deadline (YYYY-MM-DDTHH:MM:SS)
    
    Returns:
        Confirmation with task details
    """
    tasks = _load_json(TODO_FILE, [])
    
    new_task = {
        "id": str(uuid.uuid4()),
        "task": task_description,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "deadline": deadline,
    }
    
    tasks.append(new_task)
    _save_json(TODO_FILE, tasks)
    
    pending_count = len([t for t in tasks if t["status"] == "pending"])
    deadline_info = f"\nDeadline: {deadline}" if deadline else ""
    
    return f"Added: '{task_description}'{deadline_info}\n{pending_count} pending task(s)"


@tool
def list_tasks() -> str:
    """
    Get all pending tasks from the todo list.
    
    Returns:
        Numbered list of pending tasks
    """
    tasks = _load_json(TODO_FILE, [])
    pending = [t for t in tasks if t["status"] == "pending"]
    
    if not pending:
        return "Your to-do list is empty!"
    
    lines = ["**Current To-Do List:**"]
    for i, task in enumerate(pending, 1):
        created = task.get("created_at", "")[:10]
        lines.append(f"{i}. {task['task']} (added: {created})")
    
    lines.append(f"\n**Total: {len(pending)} pending task(s)**")
    return "\n".join(lines)


@tool
def complete_task(task_number: int) -> str:
    """
    Mark a task as done by its number.
    
    Args:
        task_number: Which task to complete (1, 2, 3...)
    
    Returns:
        Confirmation
    """
    tasks = _load_json(TODO_FILE, [])
    pending = [t for t in tasks if t["status"] == "pending"]
    
    if not pending:
        return "No tasks to complete!"
    
    if task_number < 1 or task_number > len(pending):
        return f"Invalid. Choose between 1 and {len(pending)}."
    
    task_id = pending[task_number - 1]["id"]
    task_name = pending[task_number - 1]["task"]
    
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            break
    
    _save_json(TODO_FILE, tasks)
    remaining = len([t for t in tasks if t["status"] == "pending"])
    
    return f"Done: '{task_name}'\n{remaining} task(s) remaining"


# =============================================================================
# WEB TOOLS
# =============================================================================

@tool
def read_webpage(url: str) -> str:
    """
    Fetch and read content from a webpage URL.
    
    Args:
        url: Full URL starting with http:// or https://
    
    Returns:
        Extracted text content
    """
    try:
        from integrations.web import read_web_page as _read
        return _read(url)
    except ImportError:
        return "Web tools not available."
    except Exception as e:
        return f"Error reading webpage: {str(e)[:100]}"


@tool
def get_youtube_transcript(video_url: str) -> str:
    """
    Get transcript from a YouTube video.
    
    Args:
        video_url: YouTube video URL
    
    Returns:
        Full transcript
    """
    try:
        from integrations.web import watch_youtube as _watch
        return _watch(video_url)
    except ImportError:
        return "YouTube tools not available."
    except Exception as e:
        return f"Error getting transcript: {str(e)[:100]}"


@tool
def get_news(topic: str = "general") -> str:
    """
    Get current news headlines.
    
    Args:
        topic: "tech", "ai", "world", "vietnam", or "general"
    
    Returns:
        Latest headlines
    """
    topic_urls = {
        "ai": "https://techcrunch.com/category/artificial-intelligence/",
        "tech": "https://techcrunch.com/",
        "world": "https://www.bbc.com/news/world",
        "vietnam": "https://vnexpress.net/",
        "general": "https://news.google.com/",
    }
    url = topic_urls.get(topic.lower(), topic_urls["general"])
    
    try:
        from integrations.web import get_news_headlines as _get_news
        return _get_news(url)
    except ImportError:
        return "News tools not available."
    except Exception as e:
        return f"Error getting news: {str(e)[:100]}"


# =============================================================================
# MEMORY TOOLS
# =============================================================================

def _get_chroma_collection(collection_name: str = "emo_memory"):
    """Get ChromaDB collection."""
    try:
        import chromadb
        os.makedirs(CHROMA_PATH, exist_ok=True)
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        return client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        print(f"ChromaDB error: {e}")
        return None


@tool
def remember_fact(fact: str, category: str = "other") -> str:
    """
    Save a personal fact to long-term memory (permanent).
    
    Categories: "identity", "preference", "relationship", "date", "skill", "other"
    
    Args:
        fact: Information to remember
        category: Type of information
    
    Returns:
        Confirmation
    """
    collection = _get_chroma_collection("long_term")
    if not collection:
        return "Memory system unavailable."
    
    doc_id = f"fact_{hashlib.md5(fact.encode()).hexdigest()[:8]}"
    
    try:
        collection.upsert(
            documents=[fact],
            ids=[doc_id],
            metadatas=[{"category": category, "saved_at": datetime.now().isoformat()}]
        )
        return f"Remembered: {fact}"
    except Exception as e:
        return f"Error saving: {str(e)[:50]}"


@tool
def recall_personal_info(query: str) -> str:
    """
    Search long-term memory for personal facts.
    
    Args:
        query: What to search for
    
    Returns:
        Matching facts
    """
    collection = _get_chroma_collection("long_term")
    if not collection or collection.count() == 0:
        return "No personal information saved yet."
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(5, collection.count())
        )
        
        if not results["documents"] or not results["documents"][0]:
            return "No matching information found."
        
        facts = results["documents"][0]
        return "Found:\n" + "\n".join(f"- {f}" for f in facts)
    except Exception as e:
        return f"Error searching: {str(e)[:50]}"


@tool
def search_saved_content(query: str) -> str:
    """
    Search all saved memories.
    
    Args:
        query: What to search for
    
    Returns:
        Matching content
    """
    collection = _get_chroma_collection("emo_memory")
    if not collection or collection.count() == 0:
        return "No saved content found."
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(5, collection.count())
        )
        
        if not results["documents"] or not results["documents"][0]:
            return "No matching content found."
        
        docs = results["documents"][0]
        return "Found:\n" + "\n".join(f"- {d[:200]}..." for d in docs)
    except Exception as e:
        return f"Error: {str(e)[:50]}"


# =============================================================================
# CALENDAR TOOLS
# =============================================================================

@tool
def get_calendar_events(days: int = 7) -> str:
    """
    Get upcoming calendar events.
    
    Args:
        days: Number of days to look ahead (default 7)
    
    Returns:
        List of events
    """
    try:
        from integrations.calendar import list_upcoming_events as _list
        return _list(days)
    except ImportError:
        return "Calendar not connected. Please connect Google Calendar first."
    except Exception as e:
        return f"Error: {str(e)[:100]}"


@tool
def add_calendar_event(description: str) -> str:
    """
    Add event to calendar using natural language.
    
    Examples: "Meeting tomorrow at 3pm", "Dentist Friday 10am"
    
    Args:
        description: Natural language event description
    
    Returns:
        Confirmation
    """
    try:
        from integrations.calendar import quick_add_event as _add
        return _add(description)
    except ImportError:
        return "Calendar not connected."
    except Exception as e:
        return f"Error: {str(e)[:100]}"


@tool
def search_calendar(query: str) -> str:
    """
    Search calendar for events.
    
    Args:
        query: Search term (e.g., "dentist", "meeting")
    
    Returns:
        Matching events
    """
    try:
        from integrations.calendar import search_events as _search
        return _search(query)
    except ImportError:
        return "Calendar not connected."
    except Exception as e:
        return f"Error: {str(e)[:100]}"


# =============================================================================
# QUIZ TOOL
# =============================================================================

@tool
def create_quiz(topic: str, num_questions: int = 5) -> str:
    """
    Generate an interactive quiz on a topic.
    
    Args:
        topic: Subject to quiz on
        num_questions: Number of questions (default 5)
    
    Returns:
        Quiz in JSON format
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "API key not configured."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""Generate a {num_questions}-question quiz about "{topic}".
Return ONLY valid JSON:
{{
    "title": "Quiz: {topic}",
    "questions": [
        {{
            "id": 1,
            "type": "multiple_choice",
            "question": "Question?",
            "options": ["A", "B", "C", "D"],
            "correct": 0,
            "explanation": "Why correct"
        }}
    ]
}}"""
        
        response = model.generate_content(prompt)
        return f"QUIZ_CREATED:{response.text}"
    except Exception as e:
        return f"Error creating quiz: {str(e)[:100]}"


# =============================================================================
# 3-TIER MEMORY TOOLS
# =============================================================================

_current_session_id = "default"


def set_current_session_id(session_id: str):
    """Set session ID for short-term memory scoping."""
    global _current_session_id
    _current_session_id = session_id


@tool
def save_short_term_memory(content: str, context: str, importance: str = "normal") -> str:
    """
    Save temporary context to short-term memory for THIS SESSION ONLY.
    
    Args:
        content: Information to remember
        context: Why this is relevant
        importance: "low", "normal", or "high"
    
    Returns:
        Confirmation message
    """
    try:
        collection = _get_chroma_collection("short_term_memory")
        if not collection:
            return "Memory system unavailable."
        
        doc_id = f"short_{_current_session_id[:8]}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        
        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "session_id": _current_session_id,
                "context": context,
                "importance": importance,
                "created_at": datetime.now().isoformat()
            }]
        )
        
        return f"Saved to session memory: '{content[:50]}...'"
    except Exception as e:
        return f"Error: {str(e)[:50]}"


@tool
def query_short_term_memory(query: str) -> str:
    """
    Search short-term memory for context from THIS SESSION.
    
    Args:
        query: What to search for
    
    Returns:
        Relevant short-term memories
    """
    try:
        collection = _get_chroma_collection("short_term_memory")
        if not collection or collection.count() == 0:
            return "No short-term memories stored."
        
        results = collection.query(
            query_texts=[query],
            n_results=5,
            where={"session_id": _current_session_id}
        )
        
        if not results["documents"] or not results["documents"][0]:
            return "No relevant short-term memories found."
        
        output = ["=== SESSION MEMORY ==="]
        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), 1):
            output.append(f"{i}. [{meta.get('importance', 'normal')}] {doc}")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)[:50]}"


@tool
def save_project_memory(project_name: str, content: str, content_type: str = "note") -> str:
    """
    Save project-related information.
    
    Args:
        project_name: Name of the project
        content: Information to save
        content_type: "goal", "idea", "progress", "note", "blocker"
    
    Returns:
        Confirmation
    """
    try:
        collection = _get_chroma_collection("project_memory")
        if not collection:
            return "Memory system unavailable."
        
        project_key = project_name.lower().strip().replace(" ", "_")
        doc_id = f"proj_{project_key}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        
        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "project_name": project_name,
                "project_key": project_key,
                "content_type": content_type,
                "created_at": datetime.now().isoformat()
            }]
        )
        
        return f"Saved to project '{project_name}': '{content[:50]}...'"
    except Exception as e:
        return f"Error: {str(e)[:50]}"


@tool
def query_project(project_name: str = "", query: str = "") -> str:
    """
    Search project memory.
    
    Args:
        project_name: Optional specific project
        query: What to search for
    
    Returns:
        Relevant project information
    """
    try:
        collection = _get_chroma_collection("project_memory")
        if not collection or collection.count() == 0:
            return "No projects stored."
        
        if project_name:
            project_key = project_name.lower().strip().replace(" ", "_")
            results = collection.get(
                where={"project_key": project_key},
                include=["documents", "metadatas"]
            )
            
            if not results["documents"]:
                return f"No project found: {project_name}"
            
            output = [f"=== PROJECT: {project_name} ==="]
            for doc, meta in zip(results["documents"], results["metadatas"]):
                output.append(f"• [{meta.get('content_type', 'note')}] {doc}")
            return "\n".join(output)
        
        # Search all projects
        results = collection.query(
            query_texts=[query or "project"],
            n_results=10
        )
        
        if not results["documents"] or not results["documents"][0]:
            return "No relevant project info found."
        
        output = ["=== PROJECT MEMORY ==="]
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            output.append(f"• [{meta.get('project_name', '?')}] {doc}")
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)[:50]}"


@tool
def list_projects() -> str:
    """
    List all active projects.
    
    Returns:
        List of project names and item counts
    """
    try:
        collection = _get_chroma_collection("project_memory")
        if not collection or collection.count() == 0:
            return "No projects stored."
        
        results = collection.get(include=["metadatas"])
        
        projects = {}
        for meta in results["metadatas"]:
            name = meta.get("project_name", "Unknown")
            if name not in projects:
                projects[name] = 0
            projects[name] += 1
        
        output = ["=== ACTIVE PROJECTS ==="]
        for name, count in projects.items():
            output.append(f"{name} ({count} items)")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)[:50]}"


@tool
def update_long_term_memory(old_fact: str, new_fact: str, category: str) -> str:
    """
    Update or correct a long-term memory fact.
    
    Args:
        old_fact: The fact to find and update
        new_fact: The corrected information
        category: Category of the fact
    
    Returns:
        Confirmation
    """
    try:
        collection = _get_chroma_collection("long_term")
        if not collection:
            return "Memory system unavailable."
        
        # Search for old fact
        results = collection.query(
            query_texts=[old_fact],
            n_results=1
        )
        
        if results["ids"] and results["ids"][0]:
            collection.delete(ids=results["ids"][0])
        
        # Save new fact
        doc_id = f"fact_{hashlib.md5(new_fact.encode()).hexdigest()[:8]}"
        collection.upsert(
            ids=[doc_id],
            documents=[new_fact],
            metadatas=[{"category": category, "saved_at": datetime.now().isoformat()}]
        )
        
        return f"Updated: '{old_fact[:30]}...' → '{new_fact[:30]}...'"
    except Exception as e:
        return f"Error: {str(e)[:50]}"


# =============================================================================
# EXPORT ALL TOOLS
# =============================================================================

def get_all_tools() -> list:
    """Return all 22 tools."""
    return [
        # Gmail (3)
        search_gmail,
        get_email,
        analyze_email_attachment,
        # Tasks (3)
        add_task,
        list_tasks,
        complete_task,
        # Web (3)
        read_webpage,
        get_youtube_transcript,
        get_news,
        # Memory - Basic (3)
        remember_fact,
        recall_personal_info,
        search_saved_content,
        # Memory - 3-Tier (6)
        save_short_term_memory,
        query_short_term_memory,
        save_project_memory,
        query_project,
        list_projects,  # Renamed from list_all_projects
        update_long_term_memory,
        # Calendar (3)
        get_calendar_events,
        add_calendar_event,
        search_calendar,
        # Quiz (1)
        create_quiz,
    ]

