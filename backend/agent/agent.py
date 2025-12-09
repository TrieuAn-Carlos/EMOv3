"""
EMO Backend - Enhanced LangGraph ReAct Agent
=============================================
Integrated context memory with optimized token usage.
Combines best features from both backends.
"""

import asyncio
from typing import Optional, AsyncGenerator, Dict
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

# Import from new core modules
from core import (
    GEMINI_API_KEY,
    GEMMA_27B_MODEL,
    TEMPERATURE,
    EmoState,
    initialize_context,
    format_context_block,
)
from memory import query_memory, format_memories_for_context


# Context and memory now imported from core and memory modules


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(context_state: EmoState) -> str:
    """Build complete system prompt with context."""
    context_block = format_context_block(context_state)
    
    return f"""Bạn là Emo, trợ lý AI cá nhân.

{context_block}

## QUY TẮC

1. TRẢ LỜI NGẮN GỌN - không lặp lại câu hỏi, không chào nhiều lần
2. CHỈ DÙNG TOOL khi cần dữ liệu mới (email/calendar/web)
3. EMAIL: Gọi search_gmail → hiển thị danh sách → user chọn số → get_email
4. FORMAT: Markdown, emoji vừa phải 😊"""


# =============================================================================
# AGENT
# =============================================================================

_agent = None
_context_state: EmoState = None
_llm = None
_current_provider = None


def get_or_create_agent():
    """Get or create the LangGraph agent using Gemini 2.0 Flash.
    
    Returns:
        LangGraph agent
    """
    global _agent, _context_state, _llm, _current_provider
    
    # OPTIMIZATION: Reuse agent if already created
    if _agent is not None:
        return _agent
    
    # Only initialize on first call
    _context_state = initialize_context()
    
    from core.config import MAX_OUTPUT_TOKENS
    
    # Use Gemini 2.0 Flash (supports function calling)
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required")
    
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    _llm = ChatGoogleGenerativeAI(
        model=GEMMA_27B_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=TEMPERATURE,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    _current_provider = 'gemini'
    print(f"✅ Using Gemini 2.0 Flash ({GEMMA_27B_MODEL})")
    
    # Use enhanced tools
    from agent.tools import get_all_tools
    tools = get_all_tools()
    
    _agent = create_react_agent(
        _llm,
        tools,
        prompt=build_system_prompt(_context_state),
    )
    
    print("✅ Agent initialized (will be reused)")
    return _agent


def get_session_messages(session_id: Optional[str], db: Session) -> list:
    """Get conversation history for a session from database."""
    if not session_id or not db:
        return []
    
    from services.session_service import SessionService
    service = SessionService(db)
    
    messages = service.get_session_messages(session_id, limit=20)
    return [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]


def save_session_message(session_id: Optional[str], role: str, content: str, db: Session) -> dict:
    """Save a single message to session in database."""
    if not session_id or not db:
        return {"saved": False, "count": 0, "warning": None, "limit_reached": False}
    
    from services.session_service import SessionService
    service = SessionService(db)
    
    return service.save_message(session_id, role, content, auto_create_session=True)


async def chat_with_agent(
    user_message: str,
    memory_context: str = "",
    session_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> dict:
    """Process a user message through the LangGraph agent with robust error handling."""
    
    result = {
        "response": "",
        "thinking": "",
        "tools_used": [],
        "error": None,
    }
    
    try:
        agent = get_or_create_agent()
    except Exception as e:
        result["error"] = f"Agent initialization error: {str(e)[:200]}"
        result["response"] = "❌ Xin lỗi, có lỗi khi khởi tạo agent. Vui lòng thử lại sau."
        return result
    
    # Build input - OPTIMIZE by reducing context
    parts = []
    
    # OPTIMIZATION: Skip session history for first message (too much context)
    # Let agent handle fresh each time - faster response
    
    # OPTIMIZATION: Skip memory query for simple greetings/short messages
    simple_greetings = ["chào", "hi", "hello", "hey", "xin chào", "ok", "yes"]
    is_simple = any(g in user_message.lower() for g in simple_greetings) and len(user_message) < 20
    
    if not is_simple:
        # Only query memory for complex questions
        try:
            memories = query_memory(user_message, n_results=2)  # Reduce from 5 to 2
            if memories:
                mem_formatted = format_memories_for_context(memories)
                if mem_formatted:
                    parts.append(f"[Bộ nhớ liên quan]:\n{mem_formatted}")
        except Exception as e:
            print(f"Memory query warning: {e}")
            # Continue without memories
    
    # Add current user message
    parts.append(f"[User]: {user_message}")
    
    full_input = "\n\n".join(parts) if parts else user_message
    
    # Convert to LangChain format
    lc_messages = [HumanMessage(content=full_input)]
    
    try:
        loop = asyncio.get_event_loop()
        agent_response = await loop.run_in_executor(
            None,
            lambda: agent.invoke({"messages": lc_messages})
        )
        
        final_messages = agent_response.get("messages", [])
        
        thinking_parts = []
        email_list_output = ""
        email_content_output = ""
        
        for msg in final_messages:
            # Track tool calls
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    result["tools_used"].append(tool_name)
                    thinking_parts.append(f"Called: {tool_name}")
            
            # Extract tool output (ToolMessage)
            if hasattr(msg, "name"):
                if msg.name == "search_gmail" and hasattr(msg, "content") and msg.content:
                    email_list_output = str(msg.content)
                elif msg.name == "get_email" and hasattr(msg, "content") and msg.content:
                    email_content_output = str(msg.content)
        
        # Get AI's final response
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                content = msg.content
                if isinstance(content, list):
                    text_parts = [
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    ]
                    result["response"] = " ".join(text_parts)
                else:
                    result["response"] = str(content)
                break
        
        # CRITICAL: Force include tool outputs if AI doesn't show them
        if email_list_output and "search_gmail" in result["tools_used"]:
            if "[1]" not in result["response"] and "Found" not in result["response"]:
                result["response"] = email_list_output + "\n\n" + result["response"]
        
        if email_content_output and "get_email" in result["tools_used"]:
            if "**Email #" not in result["response"] and "**Subject:**" not in result["response"]:
                result["response"] = email_content_output + "\n\n" + result["response"]
        
        if thinking_parts:
            result["thinking"] = "\n".join(thinking_parts)
        
        # Fallback if no response generated
        if not result["response"]:
            result["response"] = "Xin lỗi, tôi không tạo được câu trả lời. Vui lòng thử lại."
        
        # Save messages to database
        if session_id and db and result["response"]:
            try:
                save_session_message(session_id, "user", user_message, db)
                save_session_message(session_id, "assistant", result["response"], db)
            except Exception as e:
                print(f"Database save warning: {e}")
                # Continue even if save fails
        
    except Exception as e:
        error_msg = str(e)
        result["error"] = error_msg
        
        # Provide user-friendly error messages
        if "tool_use_failed" in error_msg.lower():
            result["response"] = "❌ Có lỗi khi sử dụng công cụ. Tôi sẽ thử trả lời trực tiếp.\n\n"
            result["response"] += "Vui lòng mô tả chi tiết hơn hoặc thử cách hỏi khác."
        elif "rate_limit" in error_msg.lower():
            result["response"] = "⏳ API đang quá tải. Vui lòng đợi vài giây và thử lại."
        elif "timeout" in error_msg.lower():
            result["response"] = "⏱️ Xử lý quá lâu. Vui lòng thử lại với câu hỏi ngắn gọn hơn."
        else:
            result["response"] = f"❌ Có lỗi xảy ra: {error_msg[:150]}...\n\nVui lòng thử lại."
        
        print(f"Agent error: {e}")
        import traceback
        print(traceback.format_exc())
    
    return result


async def stream_chat_with_agent(
    user_message: str,
    session_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> AsyncGenerator[dict, None]:
    """Stream chat response."""
    result = await chat_with_agent(user_message, session_id=session_id, db=db)
    
    for tool in result.get("tools_used", []):
        yield {"type": "tool", "name": tool}
    
    response = result.get("response", "")
    chunk_size = 20
    for i in range(0, len(response), chunk_size):
        yield {"type": "text", "content": response[i:i+chunk_size]}
        await asyncio.sleep(0.02)
    
    yield {"type": "done", "full_response": response}
