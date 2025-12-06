"""
EMO2 - Memory Tools Module
==========================
3-Tier memory system with ChromaDB for semantic search.

Memory Types:
- SHORT-TERM: Session-scoped, auto-expires
- LONG-TERM: Permanent personal facts
- PROJECT: Active projects and goals

Author: Joshua
Version: 3.0 (Refactored)
"""

from langchain_core.tools import tool


# =============================================================================
# TOOL 1: MEMORY SEARCH (ChromaDB Integration)
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



