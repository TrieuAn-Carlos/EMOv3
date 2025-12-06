"""
Emo2 - Universal Context State Schema
=====================================
Central Memory Module for the LangGraph Agent

This module implements the "4 Pillars of Context" architecture:
1. IdentityContext - WHO: Static user identity and preferences
2. EnvironmentContext - WHEN/WHERE: Real-time situational awareness  
3. WorkingMemory - WHAT NOW: Temporary active data from tools
4. Artifacts - OUTCOMES: Structured actionable items

Author: Senior AI Architect
Version: 2.0
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph.message import add_messages


# =============================================================================
# PILLAR 1: IDENTITY CONTEXT
# =============================================================================

class IdentityContext(TypedDict):
    """
    Stores static user information and preferences.
    This context remains stable across sessions.
    
    Fields:
        user_name: The user's display name
        role: User's role/occupation (e.g., "developer", "manager", "student")
        communication_style: Preferred interaction style (e.g., "formal", "casual", "technical")
        long_term_facts: Permanent personal facts organized by category (never forgets)
    """
    user_name: str
    role: str
    communication_style: str
    long_term_facts: Dict[str, List[str]]


# =============================================================================
# PILLAR 2: ENVIRONMENT CONTEXT
# =============================================================================

class EnvironmentContext(TypedDict):
    """
    Stores real-time situational awareness.
    Updated at the start of each graph invocation.
    
    Fields:
        current_time: Human-readable time (e.g., "15:30")
        current_date: Human-readable date (e.g., "Wednesday, Dec 3, 2025")
        location: User's location if available
    """
    current_time: str
    current_date: str
    location: str


# =============================================================================
# PILLAR 3: WORKING MEMORY
# =============================================================================

class WorkingMemory(TypedDict):
    """
    Stores temporary active data retrieved from tools.
    This is NOT chat history - it's the content being actively worked on.
    
    Fields:
        active_content: The main content being processed (email body, webpage text, document content)
        source_url: Optional URL or reference to the content source
    """
    active_content: str
    source_url: Optional[str]


# =============================================================================
# PILLAR 4: ARTIFACTS
# =============================================================================

class CalendarEvent(TypedDict):
    """Structure for calendar events."""
    title: str
    datetime: str
    description: Optional[str]


class Artifacts(TypedDict):
    """
    Stores structured outcomes and actionable items.
    These are concrete outputs that persist across the conversation.
    
    Fields:
        todo_list: List of pending tasks/action items
        pending_calendar_events: List of scheduled or proposed events
    """
    todo_list: List[str]
    pending_calendar_events: List[Dict[str, Any]]


# =============================================================================
# MAIN GRAPH STATE
# =============================================================================

class EmoState(TypedDict):
    """
    The Central Memory for Emo2 Agent.
    
    Aggregates the 4 Pillars of Context into a single LangGraph-compatible state.
    
    Structure:
        messages: Chat history with automatic message appending (LangGraph standard)
        identity: IdentityContext - Static user info
        env: EnvironmentContext - Real-time situational awareness
        memory: WorkingMemory - Temporary active data from tools
        artifacts: Artifacts - Structured outcomes (todos, events)
    """
    # Standard LangGraph message history with reducer
    messages: Annotated[list, add_messages]
    
    # The 4 Pillars of Context
    identity: IdentityContext
    env: EnvironmentContext
    memory: WorkingMemory
    artifacts: Artifacts


# =============================================================================
# CONFIGURATION
# =============================================================================

USER_CONFIG_FILE = "user_config.json"
TODO_FILE = "todo.json"

DEFAULT_IDENTITY = IdentityContext(
    user_name="User",
    role="general",
    communication_style="friendly",
    long_term_facts={}
)


# =============================================================================
# LOGIC & HELPERS
# =============================================================================

def get_current_datetime() -> tuple[str, str]:
    """
    Get current date and time in human-readable format.
    
    Returns:
        Tuple of (time_str, date_str)
        - time_str: "15:30" format
        - date_str: "Wednesday, Dec 3, 2025" format
    """
    now = datetime.now()
    
    # Human-readable time: "15:30"
    time_str = now.strftime("%H:%M")
    
    # Human-readable date: "Wednesday, Dec 3, 2025"
    date_str = now.strftime("%A, %b %d, %Y")
    
    return time_str, date_str


def load_identity_from_config() -> IdentityContext:
    """
    Load user identity from configuration file.
    Returns default identity if file doesn't exist.
    Includes long_term_facts for permanent personal memories.
    """
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return IdentityContext(
                    user_name=config.get('name', DEFAULT_IDENTITY['user_name']),
                    role=config.get('role', DEFAULT_IDENTITY['role']),
                    communication_style=config.get('preferences', {}).get(
                        'communication_style', 
                        DEFAULT_IDENTITY['communication_style']
                    ),
                    long_term_facts=config.get('long_term_facts', {})
                )
        except (json.JSONDecodeError, IOError):
            pass
    
    return DEFAULT_IDENTITY


def load_todo_list() -> List[str]:
    """
    Load todo list from the existing todo.json file.
    Returns only pending task descriptions.
    """
    if os.path.exists(TODO_FILE):
        try:
            with open(TODO_FILE, 'r') as f:
                tasks = json.load(f)
                # Extract only pending tasks
                return [
                    task.get('task', '') 
                    for task in tasks 
                    if task.get('status') == 'pending'
                ]
        except (json.JSONDecodeError, IOError):
            pass
    
    return []


def initialize_context() -> EmoState:
    """
    Initialize a fresh EmoState with real-time context.
    
    This function:
    1. Captures current system time for EnvironmentContext
    2. Loads user identity from config
    3. Loads existing todos into Artifacts
    4. Initializes empty WorkingMemory
    
    Returns:
        A fully initialized EmoState ready for graph execution
    """
    # Capture real-time environment
    current_time, current_date = get_current_datetime()
    
    # Load identity from config
    identity = load_identity_from_config()
    
    # Load existing todos
    todo_list = load_todo_list()
    
    return EmoState(
        messages=[],
        identity=identity,
        env=EnvironmentContext(
            current_time=current_time,
            current_date=current_date,
            location="Unknown"  # Can be enhanced with geolocation
        ),
        memory=WorkingMemory(
            active_content="",
            source_url=None
        ),
        artifacts=Artifacts(
            todo_list=todo_list,
            pending_calendar_events=[]
        )
    )


def refresh_environment(state: EmoState) -> Dict[str, EnvironmentContext]:
    """
    Refresh only the environment context with current time.
    Use this as a node to update time at graph start.
    
    Args:
        state: Current EmoState
        
    Returns:
        State update dict with refreshed environment
    """
    current_time, current_date = get_current_datetime()
    
    return {
        "env": EnvironmentContext(
            current_time=current_time,
            current_date=current_date,
            location=state.get('env', {}).get('location', 'Unknown')
        )
    }


def update_working_memory(
    state: EmoState, 
    content: str, 
    source: Optional[str] = None
) -> Dict[str, WorkingMemory]:
    """
    Update the working memory with new content.
    
    Args:
        state: Current EmoState
        content: The active content to store
        source: Optional source URL/reference
        
    Returns:
        State update dict with new working memory
    """
    return {
        "memory": WorkingMemory(
            active_content=content,
            source_url=source
        )
    }


def clear_working_memory(state: EmoState) -> Dict[str, WorkingMemory]:
    """
    Clear the working memory.
    
    Returns:
        State update dict with empty working memory
    """
    return {
        "memory": WorkingMemory(
            active_content="",
            source_url=None
        )
    }


def add_todo(state: EmoState, task: str) -> Dict[str, Artifacts]:
    """
    Add a task to the todo list in artifacts.
    
    Args:
        state: Current EmoState
        task: Task description to add
        
    Returns:
        State update dict with updated artifacts
    """
    current_artifacts = state.get('artifacts', {})
    current_todos = list(current_artifacts.get('todo_list', []))
    current_todos.append(task)
    
    return {
        "artifacts": Artifacts(
            todo_list=current_todos,
            pending_calendar_events=current_artifacts.get('pending_calendar_events', [])
        )
    }


def add_calendar_event(
    state: EmoState, 
    title: str, 
    event_datetime: str, 
    description: Optional[str] = None
) -> Dict[str, Artifacts]:
    """
    Add a calendar event to artifacts.
    
    Args:
        state: Current EmoState
        title: Event title
        event_datetime: When the event occurs
        description: Optional event description
        
    Returns:
        State update dict with updated artifacts
    """
    current_artifacts = state.get('artifacts', {})
    current_events = list(current_artifacts.get('pending_calendar_events', []))
    
    current_events.append({
        "title": title,
        "datetime": event_datetime,
        "description": description
    })
    
    return {
        "artifacts": Artifacts(
            todo_list=current_artifacts.get('todo_list', []),
            pending_calendar_events=current_events
        )
    }


# =============================================================================
# SYSTEM PROMPT FORMATTER
# =============================================================================

def format_system_prompt(state: EmoState) -> str:
    """
    Format the state into a structured string for the LLM's system instruction.
    
    Uses Markdown headers for clear organization:
    - ### IDENTITY: Who the user is
    - ### CURRENT CONTEXT: Time and location awareness
    - ### ACTIVE MEMORY: Content currently being processed
    - ### ARTIFACTS: Todos and scheduled events
    
    Args:
        state: The current EmoState
        
    Returns:
        Formatted string block for system prompt injection
    """
    sections = []
    
    # === IDENTITY SECTION ===
    identity = state.get('identity', {})
    identity_block = f"""### IDENTITY
- **User**: {identity.get('user_name', 'Unknown')}
- **Role**: {identity.get('role', 'general')}
- **Communication Style**: {identity.get('communication_style', 'friendly')}"""
    sections.append(identity_block)
    
    # === LONG-TERM MEMORY SECTION (Permanent Facts) ===
    long_term_facts = identity.get('long_term_facts', {})
    if long_term_facts and any(long_term_facts.values()):
        facts_parts = ["### LONG-TERM MEMORY (Permanent Facts)"]
        for category, facts in long_term_facts.items():
            if facts:
                facts_parts.append(f"**{category.title()}**:")
                for fact in facts[:5]:  # Limit to 5 per category for prompt space
                    facts_parts.append(f"  - {fact}")
        facts_block = "\n".join(facts_parts)
        sections.append(facts_block)
    
    # === CURRENT CONTEXT SECTION ===
    env = state.get('env', {})
    context_block = f"""### CURRENT CONTEXT
- **Date**: {env.get('current_date', 'Unknown')}
- **Time**: {env.get('current_time', 'Unknown')}
- **Location**: {env.get('location', 'Unknown')}"""
    sections.append(context_block)
    
    # === ACTIVE MEMORY SECTION ===
    memory = state.get('memory', {})
    active_content = memory.get('active_content', '')
    source_url = memory.get('source_url')
    
    if active_content:
        # Truncate very long content for the prompt
        display_content = active_content
        if len(active_content) > 2000:
            display_content = active_content[:2000] + "\n... [content truncated]"
        
        source_line = f"\n- **Source**: {source_url}" if source_url else ""
        memory_block = f"""### ACTIVE MEMORY
{source_line}
```
{display_content}
```"""
    else:
        memory_block = """### ACTIVE MEMORY
_No active content loaded._"""
    sections.append(memory_block)
    
    # === ARTIFACTS SECTION ===
    artifacts = state.get('artifacts', {})
    
    # Format todo list
    todo_list = artifacts.get('todo_list', [])
    if todo_list:
        todo_items = "\n".join(f"  {i+1}. {task}" for i, task in enumerate(todo_list))
        todo_block = f"**📋 To-Do List** ({len(todo_list)} items):\n{todo_items}"
    else:
        todo_block = "**📋 To-Do List**: _Empty_"
    
    # Format calendar events
    events = artifacts.get('pending_calendar_events', [])
    if events:
        event_items = "\n".join(
            f"  • {e.get('title', 'Untitled')} @ {e.get('datetime', 'TBD')}"
            for e in events
        )
        events_block = f"**📅 Pending Events** ({len(events)} events):\n{event_items}"
    else:
        events_block = "**📅 Pending Events**: _None scheduled_"
    
    artifacts_block = f"""### ARTIFACTS
{todo_block}

{events_block}"""
    sections.append(artifacts_block)
    
    # === COMBINE ALL SECTIONS ===
    formatted = "\n\n".join(sections)
    
    return f"""
╔══════════════════════════════════════════════════════════════╗
║                    UNIVERSAL CONTEXT                         ║
╚══════════════════════════════════════════════════════════════╝

{formatted}

═══════════════════════════════════════════════════════════════
"""


def build_full_system_prompt(base_instruction: str, state: EmoState) -> str:
    """
    Build a complete system prompt by combining base instructions with context.
    
    Args:
        base_instruction: The base system prompt for Emo2
        state: Current EmoState
        
    Returns:
        Complete system prompt string
    """
    context_block = format_system_prompt(state)
    
    return f"""{base_instruction}

{context_block}

**Instructions for using context:**
- Address the user by their name when appropriate
- Adapt your communication style to match their preference
- Be aware of the current time and date for scheduling
- Reference active memory content when answering questions about it
- Proactively manage the to-do list and calendar events
"""


# =============================================================================
# TESTING / DEBUG
# =============================================================================

if __name__ == "__main__":
    """
    Test the state module independently.
    """
    print("=" * 64)
    print("        Emo2 State Module - 4 Pillars of Context")
    print("=" * 64)
    
    # Initialize context
    print("\n🔧 Initializing context...")
    state = initialize_context()
    print("✅ Context initialized successfully!")
    
    # Display each pillar
    print("\n" + "─" * 64)
    print("PILLAR 1 - IDENTITY:")
    print(f"  User: {state['identity']['user_name']}")
    print(f"  Role: {state['identity']['role']}")
    print(f"  Style: {state['identity']['communication_style']}")
    
    print("\n" + "─" * 64)
    print("PILLAR 2 - ENVIRONMENT:")
    print(f"  Date: {state['env']['current_date']}")
    print(f"  Time: {state['env']['current_time']}")
    print(f"  Location: {state['env']['location']}")
    
    print("\n" + "─" * 64)
    print("PILLAR 3 - WORKING MEMORY:")
    print(f"  Active Content: {state['memory']['active_content'] or '(empty)'}")
    print(f"  Source URL: {state['memory']['source_url'] or '(none)'}")
    
    print("\n" + "─" * 64)
    print("PILLAR 4 - ARTIFACTS:")
    print(f"  Todo Items: {len(state['artifacts']['todo_list'])}")
    for i, task in enumerate(state['artifacts']['todo_list'], 1):
        print(f"    {i}. {task}")
    print(f"  Calendar Events: {len(state['artifacts']['pending_calendar_events'])}")
    
    # Display formatted system prompt
    print("\n" + "=" * 64)
    print("FORMATTED SYSTEM PROMPT:")
    print("=" * 64)
    print(format_system_prompt(state))
    
    # Test with base instruction
    print("\n" + "=" * 64)
    print("FULL SYSTEM PROMPT (with base instruction):")
    print("=" * 64)
    base = "You are Emo2, an intelligent AI assistant with Gmail access."
    full_prompt = build_full_system_prompt(base, state)
    print(full_prompt[:1500] + "..." if len(full_prompt) > 1500 else full_prompt)
