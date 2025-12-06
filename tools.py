"""
Emo2 - Structured Tools Module
==============================
LangChain-compatible tools for the LangGraph Agent

This module provides tools optimized for 7B models:
- read_web_page: Fetch web content with metadata injection
- watch_youtube: Get transcripts with time-blocking strategy
- search_memory: Query ChromaDB vector memory
- recall_memory: Get full content by document ID

Author: Joshua
Version: 2.0
"""

import re
from typing import Optional

import requests
from langchain_core.tools import tool


# =============================================================================
# TOOL 1: WEB PAGE READER
# =============================================================================

@tool
def read_web_page(url: str) -> str:
    """
    Fetch and return the main content from a web page.
    
    Use this tool when the user asks about a webpage, article, or online content.
    The content is returned in markdown format with metadata injection for context.
    
    Args:
        url: The URL of the web page to read (e.g., "https://example.com/article")
    
    Returns:
        Formatted web content with source metadata, or error message if failed.
    """
    try:
        # Validate and normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Method 1: Try Jina Reader API first (best markdown conversion)
        try:
            jina_url = f"https://r.jina.ai/{url}"
            response = requests.get(jina_url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
            })
            
            if response.status_code == 200:
                content = response.text.strip()
                
                # Validate we got meaningful content
                if content and len(content) > 100 and not content.startswith('Error'):
                    # Apply content cap for 7B model context limits
                    if len(content) > 15000:
                        content = content[:15000] + "\n\n[...Content Truncated - Too Long...]"
                    
                    # Metadata Injection: Wrap content with clear markers
                    return f"""=== WEB CONTENT START ===
Source: {url}
---
{content}
=== WEB CONTENT END ==="""
        except Exception:
            pass  # Fall through to BeautifulSoup
        
        # Method 2: Fallback to BeautifulSoup (for blocked sites)
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove noise elements
            for element in soup(["script", "style", "meta", "link", "nav", "footer", "header"]):
                element.decompose()
            
            # Find main content container
            main = soup.find('main') or soup.find('article') or soup.find('body')
            if not main:
                main = soup
            
            # Extract structured text
            parts = []
            
            # Title
            title = soup.find('h1')
            if title:
                parts.append(f"# {title.get_text(strip=True)}\n")
            
            # Headings and paragraphs
            for elem in main.find_all(['h2', 'h3', 'h4', 'p', 'li']):
                text = elem.get_text(strip=True)
                if text and len(text) > 15:
                    if elem.name.startswith('h'):
                        level = int(elem.name[1]) + 1
                        parts.append(f"{'#' * level} {text}")
                    else:
                        parts.append(text)
            
            content = "\n\n".join(parts)
            
            if content and len(content) > 100:
                if len(content) > 15000:
                    content = content[:15000] + "\n\n[...Content Truncated - Too Long...]"
                
                return f"""=== WEB CONTENT START ===
Source: {url}
Method: Direct Extraction
---
{content}
=== WEB CONTENT END ==="""
        
        except ImportError:
            return "Error: beautifulsoup4 not installed. Run: pip install beautifulsoup4"
        except Exception:
            pass
        
        return f"Error: Could not retrieve content from {url}. The page may be blocked or unavailable."
    
    except Exception as e:
        return f"Error: Failed to read web page. {str(e)[:80]}"


# =============================================================================
# TOOL 2: YOUTUBE TRANSCRIPT (Time-Blocking Strategy)
# =============================================================================

@tool
def watch_youtube(video_url: str) -> str:
    """
    Fetch and return the transcript of a YouTube video with time-blocked formatting.
    
    Use this tool when the user shares a YouTube link or asks about video content.
    Transcripts are grouped into 60-second chunks for efficient processing.
    Supports English and Vietnamese transcripts.
    
    Args:
        video_url: The YouTube video URL (supports youtube.com/watch?v= and youtu.be/ formats)
    
    Returns:
        Time-blocked transcript with video metadata, or error message if failed.
    """
    try:
        # Extract video ID using regex patterns
        video_id = None
        
        # Pattern: youtube.com/watch?v=VIDEO_ID
        match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', video_url)
        if match:
            video_id = match.group(1)
        
        # Pattern: youtu.be/VIDEO_ID
        if not video_id:
            match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', video_url)
            if match:
                video_id = match.group(1)
        
        if not video_id:
            return "Error: Could not extract video ID. Please use a valid YouTube URL."
        
        # Import and initialize API (v0.6+)
        from youtube_transcript_api import YouTubeTranscriptApi
        
        ytt = YouTubeTranscriptApi()
        transcript = None
        language_used = None
        
        # Language priority: English > Vietnamese > Any available
        for lang_code, lang_name in [('en', 'English'), ('vi', 'Vietnamese')]:
            try:
                transcript = ytt.fetch(video_id, languages=[lang_code])
                language_used = lang_name
                break
            except Exception:
                continue
        
        # Fallback: Get any available transcript
        if not transcript:
            try:
                available = ytt.list(video_id)
                if available.manually_created_transcripts:
                    first_transcript = list(available.manually_created_transcripts.values())[0]
                    transcript = first_transcript.fetch()
                    language_used = first_transcript.language
                elif available.generated_transcripts:
                    first_transcript = list(available.generated_transcripts.values())[0]
                    transcript = first_transcript.fetch()
                    language_used = first_transcript.language
            except Exception:
                return "Error: No transcripts available for this video."
        
        if not transcript or len(transcript) == 0:
            return "Error: Transcript was empty or unavailable."
        
        # === TIME-BLOCKING STRATEGY ===
        # Group transcript into 60-second chunks instead of per-line timestamps
        # This reduces token count by ~70% while maintaining temporal context
        formatted_parts = []
        current_minute = 0
        current_texts = []
        
        for entry in transcript:
            # Handle both object and dict formats
            if hasattr(entry, 'text'):
                text, start_time = entry.text, entry.start
            else:
                text = entry.get('text', '')
                start_time = entry.get('start', 0)
            
            if not text:
                continue
            
            entry_minute = int(start_time // 60)
            
            # Start new block when minute changes
            if entry_minute > current_minute:
                if current_texts:
                    timestamp = f"[{current_minute:02d}:00]"
                    formatted_parts.append(f"{timestamp} {' '.join(current_texts)}")
                
                current_minute = entry_minute
                current_texts = [text]
            else:
                current_texts.append(text)
        
        # Final block
        if current_texts:
            timestamp = f"[{current_minute:02d}:00]"
            formatted_parts.append(f"{timestamp} {' '.join(current_texts)}")
        
        if not formatted_parts:
            return "Error: Could not process transcript content."
        
        formatted_transcript = "\n\n".join(formatted_parts)
        
        # Metadata Injection: Wrap with clear context markers
        return f"""=== YOUTUBE TRANSCRIPT ===
Video ID: {video_id}
Language: {language_used or 'Unknown'}
Duration: ~{current_minute + 1} minutes
---
{formatted_transcript}
=== END TRANSCRIPT ==="""
    
    except ImportError:
        return "Error: youtube-transcript-api not installed. Run: pip install youtube-transcript-api"
    except Exception as e:
        return f"Error: Could not retrieve transcript. {str(e)[:100]}"


# =============================================================================
# TOOL 3: MEMORY SEARCH (ChromaDB Integration)
# =============================================================================

@tool
def search_memory(query: str) -> str:
    """
    Search through stored memories for relevant information.
    
    Use this tool to find previously saved emails, web pages, or documents.
    Returns summaries of matching memories with relevance scores.
    
    Args:
        query: Natural language search query describing what to find
    
    Returns:
        List of relevant memory summaries with document IDs for full retrieval.
    """
    try:
        # Import ChromaDB functions from main module
        import chromadb
        import os
        
        CHROMA_PATH = "./emo_memory"
        
        if not os.path.exists(CHROMA_PATH):
            return "No memories stored yet. Use Gmail or web tools to build memory."
        
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        
        try:
            collection = client.get_collection("emo_memory")
        except Exception:
            return "Memory collection not found. No memories stored yet."
        
        if collection.count() == 0:
            return "Memory is empty. No documents have been saved yet."
        
        # Query with relevance threshold
        results = collection.query(
            query_texts=[query],
            n_results=min(5, collection.count()),
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant memories found for your query."
        
        # Format results with relevance scoring
        output_parts = [f"Found {len(results['documents'][0])} relevant memories:\n"]
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            relevance = max(0, round((1 - distance) * 100))
            summary = metadata.get('summary', doc[:150] + '...' if len(doc) > 150 else doc)
            source = metadata.get('source', 'Unknown')
            doc_id = results['ids'][0][i-1]
            
            output_parts.append(f"{i}. [{relevance}% match] {summary}")
            output_parts.append(f"   Source: {source} | ID: {doc_id}")
            output_parts.append("")
        
        output_parts.append("Use recall_memory(doc_id) to get full content of any memory.")
        
        return "\n".join(output_parts)
    
    except Exception as e:
        return f"Error searching memory: {str(e)[:80]}"


@tool
def recall_memory(doc_id: str) -> str:
    """
    Retrieve the full content of a specific memory by its document ID.
    
    Use this after search_memory to get complete details of a relevant memory.
    
    Args:
        doc_id: The document ID from search_memory results (e.g., "email_20241203_abc123")
    
    Returns:
        Full text content of the memory with metadata.
    """
    try:
        import chromadb
        import os
        
        CHROMA_PATH = "./emo_memory"
        
        if not os.path.exists(CHROMA_PATH):
            return f"Memory not found: {doc_id}"
        
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        
        try:
            collection = client.get_collection("emo_memory")
        except Exception:
            return f"Memory not found: {doc_id}"
        
        result = collection.get(
            ids=[doc_id],
            include=['documents', 'metadatas']
        )
        
        if not result['documents'] or not result['documents'][0]:
            return f"Memory not found with ID: {doc_id}"
        
        text = result['documents'][0]
        metadata = result['metadatas'][0] if result['metadatas'] else {}
        
        # Format output with metadata header
        output_parts = ["=== FULL MEMORY CONTENT ==="]
        
        if metadata.get('subject'):
            output_parts.append(f"Subject: {metadata['subject']}")
        if metadata.get('source'):
            output_parts.append(f"Source: {metadata['source']}")
        if metadata.get('sender'):
            output_parts.append(f"From: {metadata['sender']}")
        if metadata.get('date'):
            output_parts.append(f"Date: {metadata['date']}")
        
        output_parts.append("---")
        output_parts.append(text)
        output_parts.append("=== END MEMORY ===")
        
        return "\n".join(output_parts)
    
    except Exception as e:
        return f"Error retrieving memory: {str(e)[:80]}"


# =============================================================================
# TOOL 5: 3-TIER MEMORY SYSTEM
# =============================================================================
# Memory Types:
# 1. SHORT-TERM: Temporary context (session-based, auto-expires)
# 2. LONG-TERM: Permanent identity & personal info (never forgets unless user changes)
# 3. PROJECT: Active projects with goals, progress, and context
# =============================================================================

import json
import hashlib
from datetime import datetime

CHROMA_PATH = "./emo_memory"
LONG_TERM_CONFIG = "./user_config.json"

def _get_memory_collection(collection_name: str):
    """Helper to get or create a specific memory collection."""
    import chromadb
    import os
    
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": f"Emo's {collection_name} memory"}
    )


def _generate_doc_id(prefix: str, content: str) -> str:
    """Generate unique document ID."""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}_{content_hash}"


# Session ID management - will be set by main.py
_current_session_id = None

def set_current_session_id(session_id: str):
    """Set the current session ID for short-term memory scoping."""
    global _current_session_id
    _current_session_id = session_id

def get_current_session_id() -> str:
    """Get the current session ID."""
    global _current_session_id
    return _current_session_id or "default"

def clear_session_short_term_memory(session_id: str) -> int:
    """
    Clear all short-term memories for a specific session.
    Called when starting a new chat.
    
    Returns:
        Number of memories deleted
    """
    try:
        collection = _get_memory_collection("short_term_memory")
        
        # Get all documents for this session
        results = collection.get(
            where={"session_id": session_id},
            include=['metadatas']
        )
        
        if results['ids']:
            collection.delete(ids=results['ids'])
            return len(results['ids'])
        return 0
    except Exception:
        return 0


@tool
def save_short_term_memory(content: str, context: str, importance: str = "normal") -> str:
    """
    Save temporary context to short-term memory for THIS SESSION ONLY.
    This memory is specific to the current conversation and won't carry over to new chats.
    
    Examples of when to use:
    - User mentions they're tired/busy/in a meeting
    - Temporary preferences ("use bullet points for now")
    - Current task context ("working on a report")
    
    Args:
        content: The information to remember (what to save)
        context: Why this is relevant (context/reason)
        importance: Priority level - "low", "normal", or "high"
    
    Returns:
        Confirmation message with memory ID
    """
    try:
        collection = _get_memory_collection("short_term_memory")
        
        session_id = get_current_session_id()
        doc_id = _generate_doc_id(f"short_{session_id[:8]}", content)
        
        metadata = {
            "type": "short_term",
            "session_id": session_id,  # Scope to current session
            "context": context,
            "importance": importance,
            "created_at": datetime.now().isoformat(),
            "expires_hint": "session"
        }
        
        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )
        
        return f"✓ Saved to session memory: '{content[:50]}...'"
    
    except Exception as e:
        return f"Error saving to short-term memory: {str(e)[:80]}"


@tool
def save_long_term_memory(fact: str, category: str) -> str:
    """
    Save permanent personal information to long-term memory.
    This information NEVER expires unless the user explicitly asks to change it.
    
    Use for persistent facts about the user:
    - Personal info: name, birthday, location, job title
    - Preferences: favorite tools, coding style, communication preferences
    - Relationships: family members, colleagues, friends mentioned
    - Important dates: anniversaries, deadlines, recurring events
    - Skills & interests: programming languages, hobbies, expertise
    
    Args:
        fact: The personal fact/preference to permanently remember
        category: Type of info - "identity", "preference", "relationship", "date", "skill", "other"
    
    Returns:
        Confirmation that the information is permanently stored
    """
    try:
        # Save to ChromaDB for semantic search
        collection = _get_memory_collection("long_term_memory")
        
        doc_id = _generate_doc_id("long", fact)
        
        metadata = {
            "type": "long_term",
            "category": category,
            "created_at": datetime.now().isoformat(),
            "permanent": True
        }
        
        collection.upsert(
            ids=[doc_id],
            documents=[fact],
            metadatas=[metadata]
        )
        
        # Also update user_config.json for fast loading
        try:
            with open(LONG_TERM_CONFIG, 'r') as f:
                config = json.load(f)
            
            # Add to long_term_facts section
            if "long_term_facts" not in config:
                config["long_term_facts"] = {}
            
            if category not in config["long_term_facts"]:
                config["long_term_facts"][category] = []
            
            # Avoid duplicates
            if fact not in config["long_term_facts"][category]:
                config["long_term_facts"][category].append(fact)
            
            with open(LONG_TERM_CONFIG, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        except Exception:
            pass  # ChromaDB save succeeded, config update is optional
        
        return f"✓ Permanently saved to long-term memory [{category}]: '{fact[:60]}...'"
    
    except Exception as e:
        return f"Error saving to long-term memory: {str(e)[:80]}"


@tool
def save_project_memory(
    project_name: str,
    content: str,
    content_type: str = "note"
) -> str:
    """
    Save project-related information to project memory.
    Projects persist until completed/archived by user.
    
    Use when user mentions working on:
    - School projects, assignments, homework
    - Work projects, tasks, deliverables
    - Personal projects, side projects
    - Research, learning goals
    
    Args:
        project_name: Name of the project (e.g., "Intro to CS Project", "Website Redesign")
        content: Information to save (idea, progress, note, requirement, etc.)
        content_type: Type - "goal", "idea", "progress", "note", "requirement", "blocker", "resource"
    
    Returns:
        Confirmation with project tracking info
    """
    try:
        collection = _get_memory_collection("project_memory")
        
        # Normalize project name for consistent storage
        project_key = project_name.lower().strip().replace(" ", "_")
        
        doc_id = _generate_doc_id(f"proj_{project_key}", content)
        
        metadata = {
            "type": "project",
            "project_name": project_name,
            "project_key": project_key,
            "content_type": content_type,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )
        
        return f"✓ Saved to project '{project_name}' [{content_type}]: '{content[:50]}...'"
    
    except Exception as e:
        return f"Error saving to project memory: {str(e)[:80]}"


@tool
def query_short_term(query: str) -> str:
    """
    Search short-term memory for context from THIS SESSION ONLY.
    
    Args:
        query: What to search for in recent memory
    
    Returns:
        Relevant short-term memories from current session
    """
    try:
        collection = _get_memory_collection("short_term_memory")
        
        if collection.count() == 0:
            return "No short-term memories stored yet."
        
        session_id = get_current_session_id()
        
        # First, get all memories for this session
        session_results = collection.get(
            where={"session_id": session_id},
            include=['documents', 'metadatas']
        )
        
        if not session_results['ids']:
            return "No short-term memories for this session."
        
        # Now query within session memories
        results = collection.query(
            query_texts=[query],
            n_results=min(5, len(session_results['ids'])),
            where={"session_id": session_id},
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant short-term memories found in this session."
        
        output = [f"=== SESSION MEMORY ({session_id[:8]}...) ==="]
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            relevance = max(0, round((1 - dist) * 100))
            importance = meta.get('importance', 'normal')
            context = meta.get('context', '')
            output.append(f"{i}. [{relevance}%] [{importance}] {doc}")
            if context:
                output.append(f"   Context: {context}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Error querying short-term memory: {str(e)[:80]}"


@tool
def query_long_term(query: str) -> str:
    """
    Search long-term memory for permanent personal facts.
    
    Args:
        query: What personal information to search for
    
    Returns:
        Relevant permanent facts about the user
    """
    try:
        collection = _get_memory_collection("long_term_memory")
        
        if collection.count() == 0:
            return "No long-term memories stored yet."
        
        results = collection.query(
            query_texts=[query],
            n_results=min(5, collection.count()),
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant long-term memories found."
        
        output = ["=== LONG-TERM MEMORY (Permanent) ==="]
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            relevance = max(0, round((1 - dist) * 100))
            category = meta.get('category', 'other')
            output.append(f"{i}. [{relevance}%] [{category}] {doc}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Error querying long-term memory: {str(e)[:80]}"


@tool
def query_project(project_name: str = "", query: str = "") -> str:
    """
    Search project memory. Can filter by project name or search across all projects.
    
    Args:
        project_name: Optional - specific project to search (leave empty for all projects)
        query: What to search for within projects
    
    Returns:
        Relevant project information and progress
    """
    try:
        collection = _get_memory_collection("project_memory")
        
        if collection.count() == 0:
            return "No projects stored yet."
        
        # If project name provided, filter by it
        if project_name:
            project_key = project_name.lower().strip().replace(" ", "_")
            results = collection.get(
                where={"project_key": project_key},
                include=['documents', 'metadatas']
            )
            
            if not results['documents']:
                return f"No project found with name: {project_name}"
            
            output = [f"=== PROJECT: {project_name} ==="]
            for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas']), 1):
                content_type = meta.get('content_type', 'note')
                created = meta.get('created_at', '')[:10]
                output.append(f"{i}. [{content_type}] {doc}")
                output.append(f"   Added: {created}")
            
            return "\n".join(output)
        
        # Otherwise, semantic search across all projects
        search_query = query or "project"
        results = collection.query(
            query_texts=[search_query],
            n_results=min(10, collection.count()),
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant project information found."
        
        output = ["=== PROJECT MEMORY ==="]
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            relevance = max(0, round((1 - dist) * 100))
            project = meta.get('project_name', 'Unknown')
            content_type = meta.get('content_type', 'note')
            output.append(f"{i}. [{relevance}%] [{project}] [{content_type}] {doc}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Error querying project memory: {str(e)[:80]}"


@tool
def list_all_projects() -> str:
    """
    List all active projects stored in memory.
    
    Returns:
        List of project names with their status and item counts
    """
    try:
        collection = _get_memory_collection("project_memory")
        
        if collection.count() == 0:
            return "No projects stored yet."
        
        # Get all project documents
        results = collection.get(include=['metadatas'])
        
        if not results['metadatas']:
            return "No projects found."
        
        # Group by project
        projects = {}
        for meta in results['metadatas']:
            project_name = meta.get('project_name', 'Unknown')
            content_type = meta.get('content_type', 'note')
            status = meta.get('status', 'active')
            
            if project_name not in projects:
                projects[project_name] = {
                    'status': status,
                    'types': {}
                }
            
            projects[project_name]['types'][content_type] = \
                projects[project_name]['types'].get(content_type, 0) + 1
        
        output = ["=== ACTIVE PROJECTS ==="]
        for name, info in projects.items():
            type_counts = ", ".join(f"{k}: {v}" for k, v in info['types'].items())
            output.append(f"📁 {name} [{info['status']}]")
            output.append(f"   Items: {type_counts}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Error listing projects: {str(e)[:80]}"


@tool
def update_long_term_memory(old_fact: str, new_fact: str, category: str) -> str:
    """
    Update or correct a long-term memory fact.
    Use when user wants to change previously stored personal information.
    
    Args:
        old_fact: The fact to find and update (approximate match is OK)
        new_fact: The corrected/updated information
        category: Category of the fact being updated
    
    Returns:
        Confirmation of the update
    """
    try:
        collection = _get_memory_collection("long_term_memory")
        
        # Search for the old fact
        results = collection.query(
            query_texts=[old_fact],
            n_results=1,
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['ids'] or not results['ids'][0]:
            # Not found, save as new
            return save_long_term_memory.invoke({"fact": new_fact, "category": category})
        
        # Delete old and add new
        old_id = results['ids'][0][0]
        collection.delete(ids=[old_id])
        
        # Save new fact
        doc_id = _generate_doc_id("long", new_fact)
        
        metadata = {
            "type": "long_term",
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_from": old_fact[:50],
            "permanent": True
        }
        
        collection.upsert(
            ids=[doc_id],
            documents=[new_fact],
            metadatas=[metadata]
        )
        
        # Update user_config.json
        try:
            with open(LONG_TERM_CONFIG, 'r') as f:
                config = json.load(f)
            
            if "long_term_facts" in config and category in config["long_term_facts"]:
                # Remove old fact if present
                facts = config["long_term_facts"][category]
                config["long_term_facts"][category] = [f for f in facts if old_fact not in f]
                config["long_term_facts"][category].append(new_fact)
            
            with open(LONG_TERM_CONFIG, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        
        return f"✓ Updated long-term memory: '{old_fact[:30]}...' → '{new_fact[:30]}...'"
    
    except Exception as e:
        return f"Error updating long-term memory: {str(e)[:80]}"


# =============================================================================
# TOOLS LIST (For LangGraph binding)
# =============================================================================

# Export all tools as a list for easy binding
ALL_TOOLS = [
    read_web_page,
    watch_youtube,
    search_memory,
    recall_memory,
    # 3-Tier Memory System
    save_short_term_memory,
    save_long_term_memory,
    save_project_memory,
    query_short_term,
    query_long_term,
    query_project,
    list_all_projects,
    update_long_term_memory,
]


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    """Test tools independently."""
    
    print("=" * 64)
    print("        Emo2 Tools Module - Testing")
    print("=" * 64)
    
    # Test 1: Web page reading
    print("\n📰 Test 1: read_web_page")
    print("-" * 40)
    result = read_web_page.invoke({"url": "https://www.python.org"})
    print(result[:500] + "..." if len(result) > 500 else result)
    
    # Test 2: YouTube transcript
    print("\n\n🎥 Test 2: watch_youtube")
    print("-" * 40)
    result = watch_youtube.invoke({"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    print(result[:500] + "..." if len(result) > 500 else result)
    
    # Test 3: Memory search
    print("\n\n🔍 Test 3: search_memory")
    print("-" * 40)
    result = search_memory.invoke({"query": "budget meeting"})
    print(result)
    
    print("\n" + "=" * 64)
    print("✅ All tool tests completed!")
    print("=" * 64)
