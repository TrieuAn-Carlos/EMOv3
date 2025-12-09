"""
EMO Backend - State Management
===============================
4 Pillars of Context Architecture:
1. Identity - WHO: User info and preferences
2. Environment - WHEN/WHERE: Real-time context
3. WorkingMemory - WHAT: Active tool data
4. Artifacts - OUTCOMES: Todos, events, structured data
"""

import json
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from pathlib import Path

from langgraph.graph.message import add_messages

from .config import USER_CONFIG_FILE, TODO_FILE


# =============================================================================
# PILLAR 1: IDENTITY CONTEXT
# =============================================================================

class IdentityContext(TypedDict):
    """
    Static user identity and preferences.
    Stable across sessions.
    """
    user_name: str
    role: str
    communication_style: str
    long_term_facts: Dict[str, List[str]]  # Permanent personal memories


# =============================================================================
# PILLAR 2: ENVIRONMENT CONTEXT
# =============================================================================

class EnvironmentContext(TypedDict):
    """
    Real-time situational awareness.
    Updated at graph invocation start.
    """
    current_time: str  # "15:30"
    current_date: str  # "Wednesday, Dec 3, 2025"
    location: str


# =============================================================================
# PILLAR 3: WORKING MEMORY
# =============================================================================

class WorkingMemory(TypedDict):
    """
    Temporary active data from tools.
    NOT chat history - this is the content being worked on.
    """
    active_content: str  # Email body, webpage text, document content
    source_url: Optional[str]  # URL or reference to source


# =============================================================================
# PILLAR 4: ARTIFACTS
# =============================================================================

class Artifacts(TypedDict):
    """
    Structured outcomes and actionable items.
    Persist across conversation.
    """
    todo_list: List[str]
    pending_calendar_events: List[Dict[str, Any]]


# =============================================================================
# MAIN STATE
# =============================================================================

class EmoState(TypedDict):
    """
    Central state for LangGraph agent.
    Aggregates 4 Pillars + message history.
    """
    messages: Annotated[list, add_messages]
    identity: IdentityContext
    env: EnvironmentContext
    memory: WorkingMemory
    artifacts: Artifacts


# =============================================================================
# HELPERS
# =============================================================================

def get_current_datetime() -> tuple[str, str]:
    """
    Get current time and date in human-readable format.
    
    Returns:
        (time_str, date_str)
    """
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%A, %b %d, %Y")
    return time_str, date_str


def load_identity_from_config() -> IdentityContext:
    """Load user identity from config file."""
    default = IdentityContext(
        user_name="User",
        role="general",
        communication_style="friendly",
        long_term_facts={}
    )
    
    if USER_CONFIG_FILE.exists():
        try:
            with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return IdentityContext(
                    user_name=config.get('name', default['user_name']),
                    role=config.get('role', default['role']),
                    communication_style=config.get('preferences', {}).get(
                        'communication_style', default['communication_style']
                    ),
                    long_term_facts=config.get('long_term_facts', {})
                )
        except (json.JSONDecodeError, IOError):
            pass
    return default


def load_todo_list() -> List[str]:
    """Load pending todos from file."""
    if TODO_FILE.exists():
        try:
            with open(TODO_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                return [
                    task.get('task', '') 
                    for task in tasks 
                    if task.get('status') == 'pending'
                ]
        except (json.JSONDecodeError, IOError):
            pass
    return []


def initialize_context() -> EmoState:
    """Initialize fresh EmoState with real-time context."""
    current_time, current_date = get_current_datetime()
    identity = load_identity_from_config()
    todo_list = load_todo_list()
    
    return EmoState(
        messages=[],
        identity=identity,
        env=EnvironmentContext(
            current_time=current_time,
            current_date=current_date,
            location="Unknown"
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


def format_context_block(state: EmoState) -> str:
    """Format state into context block for system prompt."""
    sections = []
    
    # Identity
    identity = state.get('identity', {})
    sections.append(f"""### IDENTITY
- **User**: {identity.get('user_name', 'Unknown')}
- **Role**: {identity.get('role', 'general')}
- **Style**: {identity.get('communication_style', 'friendly')}""")
    
    # Long-term facts
    facts = identity.get('long_term_facts', {})
    if facts and any(facts.values()):
        parts = ["### LONG-TERM MEMORY"]
        for category, items in facts.items():
            if items:
                parts.append(f"**{category.title()}**: {', '.join(items[:3])}")
        sections.append("\n".join(parts))
    
    # Environment
    env = state.get('env', {})
    sections.append(f"""### CURRENT CONTEXT
- **Date**: {env.get('current_date', 'Unknown')}
- **Time**: {env.get('current_time', 'Unknown')}""")
    
    # Artifacts
    artifacts = state.get('artifacts', {})
    todos = artifacts.get('todo_list', [])
    if todos:
        todo_items = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(todos[:5]))
        sections.append(f"### PENDING TASKS\n{todo_items}")
    
    return "\n\n".join(sections)
