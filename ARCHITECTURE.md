# Emo2 Architecture Design Document


---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [High-Level Flow](#high-level-flow)
3. [The "Universal Context" Philosophy](#the-universal-context-philosophy)
4. [7B Model Optimization Strategy](#7b-model-optimization-strategy)
5. [Core Components](#core-components)
6. [Scalability & Extensibility](#scalability--extensibility)
7. [Design Decisions](#design-decisions)
8. [Chat History System](#chat-history-system)

---

## Executive Summary

Emo2 is a LangGraph-based AI agent designed specifically to work effectively with **7B parameter models** (like Gemini Flash). The architecture prioritizes:

- **Context Efficiency**: Minimizing token usage while maximizing information density
- **Structured Memory**: Separating working memory from chat history
- **Tool Integration**: Clean, well-documented tools that return 7B-friendly formatted output

### Key Innovation

The "Universal Context" system provides the model with essential information (time, user identity, active content) in a **structured, token-efficient format** that smaller models can reliably parse and utilize.

---

## High-Level Flow

```mermaid
graph TB
    subgraph "User Interaction"
        A[👤 User Input]
    end
    
    subgraph "Context Layer"
        B[🕐 Load Context Node]
        B1[Refresh Time/Date]
        B2[Load User Identity]
        B3[Load Active Memory]
    end
    
    subgraph "Reasoning Layer"
        C[🧠 Chatbot Node]
        C1[Inject Universal Context]
        C2[Process with LLM]
        C3[Decide: Tool or Response?]
    end
    
    subgraph "Tool Layer"
        D[🔧 Tool Node]
        D1[read_web_page]
        D2[watch_youtube]
        D3[search_memory]
        D4[recall_memory]
    end
    
    subgraph "Memory Layer"
        E[💾 Update Working Memory]
        E1[ChromaDB Vector Store]
    end
    
    subgraph "Output"
        F[📤 Response to User]
    end
    
    A --> B
    B --> B1 --> B2 --> B3 --> C
    C --> C1 --> C2 --> C3
    C3 -->|Tool Call| D
    C3 -->|Direct Response| F
    D --> D1 & D2 & D3 & D4
    D1 & D2 & D3 & D4 --> E
    E --> E1
    E --> C
    C -->|Final Response| F
    
    style A fill:#e1f5fe
    style C fill:#fff3e0
    style D fill:#e8f5e9
    style E fill:#fce4ec
    style F fill:#f3e5f5
```

### Flow Description

| Step | Node | Purpose |
|------|------|---------|
| 1 | **Load Context** | Capture current time, refresh user preferences |
| 2 | **Chatbot** | Inject Universal Context → LLM reasoning |
| 3 | **Tools Condition** | Route to tools if needed, else respond |
| 4 | **Tool Execution** | Run tool, get structured output |
| 5 | **Memory Update** | Store tool output in working memory |
| 6 | **Loop Back** | Return to chatbot to process tool results |
| 7 | **Response** | Generate final answer to user |

---

## The "Universal Context" Philosophy

### Why Separate Working Memory from Chat History?

Traditional chatbots append everything to a growing message list. This approach fails with 7B models because:

| Problem | Impact on 7B Models |
|---------|---------------------|
| Context overflow | Model loses early conversation context |
| Irrelevant history | Model gets confused by old, unrelated messages |
| No structure | Model can't prioritize recent vs. old information |
| Token waste | Repeating full documents in every turn |

### The 4 Pillars Solution

```
┌─────────────────────────────────────────────────────────────────┐
│                     UNIVERSAL CONTEXT                           │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│    IDENTITY     │   ENVIRONMENT   │ WORKING MEMORY  │ ARTIFACTS │
│   (WHO)         │   (WHEN/WHERE)  │   (WHAT NOW)    │ (OUTCOMES)│
├─────────────────┼─────────────────┼─────────────────┼───────────┤
│ • User name     │ • Current time  │ • Active doc    │ • To-dos  │
│ • Role          │ • Current date  │ • Source URL    │ • Events  │
│ • Style pref    │ • Location      │ • Summary       │ • Drafts  │
└─────────────────┴─────────────────┴─────────────────┴───────────┘
```

### Implementation

```python
# state.py - The 4 Pillars as TypedDict

class EmoState(TypedDict):
    messages: Annotated[list, add_messages]  # Chat history (minimal)
    identity: IdentityContext                 # WHO
    env: EnvironmentContext                   # WHEN/WHERE
    memory: WorkingMemory                     # WHAT NOW
    artifacts: Artifacts                      # OUTCOMES
```

### Key Insight: Working Memory ≠ Chat History

| Working Memory | Chat History |
|----------------|--------------|
| **Content** being processed | **Messages** exchanged |
| Updated by **tools** | Updated by **user/AI** |
| **Structured** format | **Unstructured** text |
| **Replaced** on new task | **Appended** continuously |
| ~2000 tokens max | Can grow indefinitely |

**Example**: When user asks "summarize this YouTube video", the transcript goes into Working Memory, NOT into chat history. This means:
- The model sees the transcript once (efficiently)
- Follow-up questions reference Working Memory
- New videos replace old content (no accumulation)

---

## 7B Model Optimization Strategy

### Strategy 1: Time-Blocking for YouTube Transcripts

**Problem**: YouTube transcripts have per-line timestamps, creating excessive tokens:

```
# ❌ BAD: Per-line timestamps (70+ tokens for 1 minute)
[0:01] Hey there
[0:03] how are you
[0:05] today we're going to
[0:08] talk about something
[0:11] really interesting
...
```

**Solution**: Group into 60-second blocks:

```
# ✅ GOOD: Time-blocked format (20 tokens for same content)
[00:00] Hey there how are you today we're going to talk about 
something really interesting...

[01:00] Now let's dive into the main topic which is about 
machine learning and how it can help...
```

**Implementation** (tools.py):

```python
# Group transcript into 60-second chunks
current_minute = 0
current_texts = []

for entry in transcript:
    entry_minute = int(entry.start // 60)
    
    if entry_minute > current_minute:
        # Save previous block
        formatted_parts.append(f"[{current_minute:02d}:00] {' '.join(current_texts)}")
        current_minute = entry_minute
        current_texts = [entry.text]
    else:
        current_texts.append(entry.text)
```

**Results**:
| Metric | Per-Line | Time-Blocked | Improvement |
|--------|----------|--------------|-------------|
| Tokens (5 min video) | ~1500 | ~400 | **73% reduction** |
| Temporal context | Exact | ±30 seconds | Acceptable |
| Model comprehension | Fragmented | Coherent | **Improved** |

### Strategy 2: Metadata Injection for Web Content

**Problem**: Raw web content lacks structure for 7B models to parse:

```
# ❌ BAD: Unstructured dump
Welcome to Python.org Python is a programming language...
Downloads Documentation Community News About...
```

**Solution**: Wrap content with clear markers and metadata:

```
# ✅ GOOD: Metadata-injected format
=== WEB CONTENT START ===
Source: https://www.python.org
---
# Welcome to Python.org

Python is a programming language that lets you work quickly
and integrate systems more effectively.

## Latest News
- Python 3.12 released...
=== WEB CONTENT END ===
```

**Why This Works**:
1. **Clear boundaries**: Model knows where content starts/ends
2. **Source attribution**: Model can cite the URL
3. **Structured headers**: Markdown headings help navigation
4. **Token budget**: 15K character limit prevents overflow

### Strategy 3: Summarized Memory Retrieval

**Problem**: Retrieving full documents from ChromaDB consumes context window:

```
# ❌ BAD: Full document injection
Here are your memories:
[Full 5000 token email about Q4 budget...]
[Full 3000 token meeting notes...]
```

**Solution**: Store and retrieve summaries, with on-demand full retrieval:

```
# ✅ GOOD: Summary-first approach
[Memory Context]
#1 | 85% match | 'Q4 Budget Discussion' | from Gmail
→ Meeting scheduled Dec 15, approved budget $50K for new servers.
  [ID: email_20241203_abc123]

(Use recall_memory tool with doc_id for full content)
```

**Implementation Flow**:
```
User Query → search_memory (returns summaries)
                    ↓
            Model reads summaries
                    ↓
    Model decides: "I need full content of #1"
                    ↓
            recall_memory(doc_id)
                    ↓
        Full content returned only when needed
```

---

## Core Components

### File Structure

```
EMO/
├── agent.py          # Graph assembly & entry point
├── state.py          # EmoState definition (4 Pillars)
├── tools.py          # LangChain tools (@tool decorated)
├── main.py           # Streamlit UI (existing)
├── history.py        # Chat history persistence (JSON-based)
├── chat_history.json # Persistent chat sessions storage
├── requirements.txt  # Dependencies
└── emo_memory/       # ChromaDB persistent storage
```

### Component Responsibilities

| File | Responsibility | Key Exports |
|------|----------------|-------------|
| `state.py` | State schema, context formatting | `EmoState`, `format_system_prompt()` |
| `tools.py` | Tool implementations | `read_web_page`, `watch_youtube`, etc. |
| `agent.py` | Graph assembly, node logic | `app`, `run_agent()` |
| `main.py` | User interface | Streamlit application |
| `history.py` | Chat session persistence | `load_all_sessions`, `save_session`, `generate_title` |

### Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         agent.py                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │ load_context│───▶│   chatbot   │───▶│    tools    │          │
│  │    node     │    │    node     │◀───│    node     │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      state.py                                ││
│  │  EmoState { messages, identity, env, memory, artifacts }    ││
│  └─────────────────────────────────────────────────────────────┘│
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      tools.py                                ││
│  │  read_web_page, watch_youtube, search_memory, recall_memory ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## Scalability & Extensibility

### Adding New Tools

The architecture makes adding tools straightforward:

```python
# tools.py - Add a new tool

@tool
def check_calendar(date: str) -> str:
    """
    Check calendar events for a specific date.
    
    Args:
        date: Date to check in YYYY-MM-DD format
    
    Returns:
        List of events for that date
    """
    # Implementation here
    return formatted_events

# Add to ALL_TOOLS list
ALL_TOOLS = [
    read_web_page,
    watch_youtube,
    search_memory,
    recall_memory,
    check_calendar,  # ← New tool
]
```

The graph automatically picks up new tools because:
1. `ALL_TOOLS` is imported in `agent.py`
2. Tools are bound to LLM: `llm.bind_tools(ALL_TOOLS)`
3. `ToolNode` dispatches based on tool calls

### Adding New State Fields

To add new context pillars:

```python
# state.py - Extend EmoState

class CalendarContext(TypedDict):
    """Calendar awareness context."""
    upcoming_events: List[Dict]
    free_slots: List[str]

class EmoState(TypedDict):
    messages: Annotated[list, add_messages]
    identity: IdentityContext
    env: EnvironmentContext
    memory: WorkingMemory
    artifacts: Artifacts
    calendar: CalendarContext  # ← New pillar
```

### Adding New Nodes

To add processing steps:

```python
# agent.py - Add a new node

def post_process_node(state: EmoState) -> dict:
    """Node that runs after chatbot response."""
    # Extract action items, update todos, etc.
    return {"artifacts": updated_artifacts}

# In build_agent_graph():
graph.add_node("post_process", post_process_node)
graph.add_edge("chatbot", "post_process")  # After chatbot
graph.add_edge("post_process", END)        # Then end
```

---

## Design Decisions

### Why LangGraph over LangChain Agents?

| Aspect | LangChain AgentExecutor | LangGraph |
|--------|------------------------|-----------|
| State management | Implicit | Explicit TypedDict |
| Flow control | Black box | Visible graph |
| Debugging | Difficult | Easy (node by node) |
| Custom logic | Limited | Full control |
| Memory handling | Automatic | Manual (better for 7B) |

### Why Gemini Flash over GPT-4?

| Aspect | Gemini Flash | GPT-4 |
|--------|--------------|-------|
| Cost | ~$0.075/1M tokens | ~$30/1M tokens |
| Speed | Very fast | Slower |
| Context | 1M tokens | 128K tokens |
| Tool calling | Native support | Native support |
| Suitability | Great for agents | Overkill for many tasks |

### Why ChromaDB for Memory?

| Aspect | ChromaDB | Pinecone | FAISS |
|--------|----------|----------|-------|
| Setup | Zero config | Cloud setup | Code setup |
| Persistence | Built-in | Cloud | Manual |
| Cost | Free | Paid | Free |
| Metadata | Full support | Full support | Limited |
| Use case | Local agents | Production | Batch processing |

---

## Chat History System

### Overview

The chat history system provides persistent conversation management using a lightweight JSON-based approach.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CHAT HISTORY SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Sidebar    │────▶│  history.py  │────▶│ chat_history │    │
│  │  (main.py)   │     │  (Manager)   │     │    .json     │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │                    │                                   │
│         │                    ▼                                   │
│         │            ┌──────────────┐                           │
│         │            │ Gemini Flash │  (AI Title Generation)    │
│         │            └──────────────┘                           │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Session State: current_session_id, messages             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Structure

```json
{
  "uuid-session-id": {
    "title": "AI-Generated Title",
    "created_at": "2025-12-03T10:30:00",
    "messages": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ]
  }
}
```

### Key Functions (history.py)

| Function | Purpose |
|----------|---------|
| `load_all_sessions()` | Load all sessions from JSON |
| `save_session(id, messages)` | Persist current conversation |
| `create_new_session()` | Generate new UUID session |
| `generate_title(id, message)` | **AI-powered** title generation using Gemini |
| `delete_session(id)` | Remove a session |
| `get_sessions_sorted()` | Return sessions (newest first) |

### AI Title Generation

Titles are automatically generated using Gemini Flash when the user sends their first message:

```python
prompt = """Generate a very short title (maximum 5 words) for a conversation 
that starts with this message. Return ONLY the title, nothing else."""
```

**Benefits**:
- Meaningful, contextual titles vs. truncated text
- Fast generation (~100ms with Gemini Flash)
- Graceful fallback to truncated message if API fails

### Tech Stack

| Component | Technology |
|-----------|------------|
| Storage | JSON file (`chat_history.json`) |
| Session IDs | UUID v4 |
| Title Generation | Gemini 2.0 Flash |
| Encoding | UTF-8 (Vietnamese support) |
| UI Integration | Streamlit sidebar |

---

## Conclusion

Emo2's architecture demonstrates that sophisticated AI agents can work effectively with smaller models when designed thoughtfully. The key principles are:

1. **Structure over size**: Well-formatted context beats more tokens
2. **Separation of concerns**: Working memory ≠ Chat history
3. **Token efficiency**: Time-blocking and summarization
4. **Clear boundaries**: Metadata injection for tool outputs
5. **Extensibility**: Modular design for easy enhancement
6. **Persistent History**: Lightweight JSON-based chat sessions with AI-generated titles

This architecture serves as a template for building production-ready AI agents that respect computational constraints while delivering powerful capabilities.

---

*Document Version: 2.1*
*Last Updated: December 2025*
*Author: Senior AI Architect*
