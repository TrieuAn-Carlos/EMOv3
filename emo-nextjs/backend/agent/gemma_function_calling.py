"""
Gemma 3 27B Function Calling Agent
===================================
Manual function calling implementation following Google's official documentation:
https://ai.google.dev/gemma/docs/capabilities/function-calling
"""

import json
import re
import asyncio
from typing import Optional, Dict, List, Any, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from core import (
    GEMINI_API_KEY,
    TEMPERATURE,
    EmoState,
    initialize_context,
    format_context_block,
)
from memory import query_memory, format_memories_for_context
from agent.tools import get_all_tools


# =============================================================================
# GEMMA FUNCTION CALLING PROMPT BUILDER
# =============================================================================

def build_function_definitions() -> str:
    """Build function definitions in Gemma format."""
    tools = get_all_tools()
    
    definitions = []
    for tool in tools:
        # Extract tool schema
        schema = tool.args_schema.schema() if hasattr(tool, 'args_schema') and tool.args_schema else {}
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        func_def = {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": required
            }
        }
        
        # Build parameters
        for param_name, param_info in properties.items():
            func_def["parameters"]["properties"][param_name] = {
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", "")
            }
        
        definitions.append(func_def)
    
    return json.dumps(definitions, indent=2)


def build_gemma_prompt(user_message: str, context_state: EmoState, memory_context: str = "", conversation_history: str = "") -> str:
    """Build complete Gemma function calling prompt."""
    
    context_block = format_context_block(context_state)
    function_defs = build_function_definitions()
    
    prompt = f"""You are Emo, a personal AI assistant with access to functions.

FUNCTION CALLING INSTRUCTIONS:
- If you need to use a function, output ONLY this JSON format:
  {{"name": "function_name", "parameters": {{"param1": "value1", "param2": "value2"}}}}
- Do NOT include any other text when calling a function
- If you don't need a function, respond directly in Vietnamese

AVAILABLE FUNCTIONS:
{function_defs}

SYSTEM CONTEXT:
{context_block}

CRITICAL RULES:
1. Keep responses SHORT and FRIENDLY - trả lời ngắn gọn, thân thiện
2. Format responses with Markdown and emojis 😊
3. Always respond in Vietnamese unless user specifies otherwise
4. ALWAYS use the conversation history below for context

FUNCTION USAGE RULES:
- search_web: ONLY use when user explicitly asks to search OR when you genuinely don't know the answer
- Email/Calendar tools: Use when user asks about emails, calendar, tasks
- PREFER answering from your own knowledge first - you are very knowledgeable!
- DO NOT search web for basic knowledge questions like math, science, history, etc.

IMPORTANT - NEVER DO THESE:
- NEVER mention tool errors, 404 errors, or "không tìm thấy trang" - just answer naturally
- NEVER apologize for errors - if a search fails, just answer from your knowledge
- NEVER include Wikipedia links or source URLs unless user explicitly asks for links
- NEVER say "Rất tiếc" or apologize unnecessarily
- If a tool fails, seamlessly provide the answer yourself without mentioning the failure
"""
    
    if memory_context:
        prompt += f"\nRELEVANT MEMORIES:\n{memory_context}\n"
    
    if conversation_history:
        prompt += f"\nCONVERSATION HISTORY:\n{conversation_history}\n"
    
    prompt += f"\nUSER REQUEST:\n{user_message}\n\nYour response:"
    
    return prompt


# =============================================================================
# FUNCTION EXECUTION
# =============================================================================

def parse_function_call(response: str) -> Optional[Dict]:
    """Parse Gemma function call from response."""
    
    # First, try to extract from code blocks
    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(code_block_pattern, response, re.DOTALL)
    
    if matches:
        try:
            parsed = json.loads(matches[0])
            if "name" in parsed and "parameters" in parsed:
                return parsed
        except:
            pass
    
    # Try to find complete JSON object with proper nesting
    # Look for the outermost braces that contain "name" and "parameters"
    start_idx = response.find('{')
    if start_idx != -1:
        brace_count = 0
        for i in range(start_idx, len(response)):
            if response[i] == '{':
                brace_count += 1
            elif response[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found matching closing brace
                    json_str = response[start_idx:i+1]
                    try:
                        parsed = json.loads(json_str)
                        if "name" in parsed and "parameters" in parsed:
                            return parsed
                    except:
                        pass
                    break
    
    return None


def execute_function(function_call: Dict, tools_map: Dict) -> str:
    """Execute a function call."""
    func_name = function_call.get("name")
    parameters = function_call.get("parameters", {})
    
    if func_name not in tools_map:
        return f"Error: Function '{func_name}' not found"
    
    tool = tools_map[func_name]
    
    try:
        result = tool.invoke(parameters)
        return str(result)
    except Exception as e:
        return f"Error executing {func_name}: {str(e)}"


# =============================================================================
# GEMMA AGENT
# =============================================================================

_gemma_llm = None
_gemma_context_state = None
_gemma_tools_map = None


def get_gemma_llm():
    """Get or create Gemma LLM instance."""
    global _gemma_llm
    
    if _gemma_llm is None:
        from core.config import MAX_OUTPUT_TOKENS
        
        _gemma_llm = ChatGoogleGenerativeAI(
            model="gemma-3-27b-it",
            api_key=GEMINI_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        print("✅ Gemma 3 27B initialized for function calling")
    
    return _gemma_llm


def get_gemma_tools_map():
    """Get tools as a dictionary."""
    global _gemma_tools_map
    
    if _gemma_tools_map is None:
        tools = get_all_tools()
        _gemma_tools_map = {tool.name: tool for tool in tools}
    
    return _gemma_tools_map


async def chat_with_gemma(
    user_message: str,
    session_id: Optional[str] = None,
    db: Optional[Session] = None,
    max_iterations: int = 5
) -> Dict:
    """
    Chat with Gemma using manual function calling.
    
    Args:
        user_message: User's message
        session_id: Session ID for history
        db: Database session
        max_iterations: Maximum function calling iterations
        
    Returns:
        Dict with response, tools_used, thinking
    """
    result = {
        "response": "",
        "thinking": "",
        "tools_used": [],
        "error": None,
    }
    
    try:
        # Initialize
        global _gemma_context_state
        if _gemma_context_state is None:
            _gemma_context_state = initialize_context()
        
        llm = get_gemma_llm()
        tools_map = get_gemma_tools_map()
        
        # Load session history from database
        session_history_str = ""
        if session_id and db:
            try:
                from agent.agent import get_session_messages
                history_messages = get_session_messages(session_id, db)
                if history_messages:
                    # Format history as conversation
                    history_lines = []
                    for msg in history_messages[-10:]:  # Last 10 messages for context
                        role = "User" if msg["role"] == "user" else "Emo"
                        content = msg["content"][:500]  # Truncate long messages
                        history_lines.append(f"{role}: {content}")
                    session_history_str = "\n".join(history_lines)
                    print(f"📚 Loaded {len(history_messages)} messages from session history")
            except Exception as e:
                print(f"Session history load warning: {e}")
        
        # Query memory for context
        memory_context = ""
        simple_greetings = ["chào", "hi", "hello", "hey", "xin chào", "ok", "yes"]
        is_simple = any(g in user_message.lower() for g in simple_greetings) and len(user_message) < 20
        
        if not is_simple:
            try:
                memories = query_memory(user_message, n_results=2)
                if memories:
                    mem_formatted = format_memories_for_context(memories)
                    if mem_formatted:
                        memory_context = mem_formatted
            except Exception as e:
                print(f"Memory query warning: {e}")
        
        # Build initial prompt with session history
        prompt = build_gemma_prompt(user_message, _gemma_context_state, memory_context, session_history_str)
        
        # Iterative function calling
        conversation_history = []
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Get LLM response
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content.strip()
            
            print(f"\n{'='*60}")
            print(f"Iteration {iteration}")
            print(f"Response: {response_text[:300]}...")
            print(f"{'='*60}\n")
            
            conversation_history.append({
                "iteration": iteration,
                "prompt": prompt[:200] + "...",
                "response": response_text[:500]
            })
            
            # Check for function call
            function_call = parse_function_call(response_text)
            
            if function_call:
                print(f"✅ Function call detected: {function_call['name']}")
                print(f"   Parameters: {function_call['parameters']}")
                
                # Execute function
                func_name = function_call.get("name")
                result["tools_used"].append(func_name)
                result["thinking"] += f"[Iteration {iteration}] Called: {func_name}\n"
                
                func_result = execute_function(function_call, tools_map)
                print(f"📦 Function result (first 200 chars): {str(func_result)[:200]}...")
                
                # Build next prompt with function result - NO MORE FUNCTION CALLING
                prompt = f"""The function has been executed and returned this result:

{func_result}

Now, based on this result, provide a clear and helpful response to the user's original request: "{user_message}"

IMPORTANT INSTRUCTIONS:
- DO NOT call any more functions
- DO NOT output JSON
- Just provide a natural, conversational response in Vietnamese
- Use Markdown formatting if needed
- Keep it concise and friendly
- Add emojis if appropriate

Your response:"""
                
            else:
                print(f"💬 No function call - treating as final response")
                # No function call, this is the final response
                result["response"] = response_text
                break
        
        # If max iterations reached without final response
        if not result["response"]:
            result["response"] = "Xin lỗi, tôi đang gặp khó khăn trong việc xử lý yêu cầu này. Vui lòng thử lại."
        
        # Save to database
        if session_id and db and result["response"]:
            try:
                from agent.agent import save_session_message
                save_session_message(session_id, "user", user_message, db)
                save_session_message(session_id, "assistant", result["response"], db)
                
                # Auto-generate title after 3 messages
                from services.session_service import SessionService
                service = SessionService(db)
                service.auto_generate_title_if_needed(session_id)
            except Exception as e:
                print(f"Database save warning: {e}")
        
    except Exception as e:
        error_msg = str(e)
        result["error"] = error_msg
        result["response"] = f"❌ Có lỗi xảy ra: {error_msg[:150]}...\n\nVui lòng thử lại."
        print(f"Gemma agent error: {e}")
        import traceback
        print(traceback.format_exc())
    
    return result


async def stream_chat_with_gemma(
    user_message: str,
    session_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> AsyncGenerator[dict, None]:
    """Stream chat response from Gemma."""
    result = await chat_with_gemma(user_message, session_id=session_id, db=db)
    
    # Stream tools
    for tool in result.get("tools_used", []):
        yield {"type": "tool", "name": tool}
    
    # Stream response
    response = result.get("response", "")
    chunk_size = 20
    for i in range(0, len(response), chunk_size):
        yield {"type": "text", "content": response[i:i+chunk_size]}
        await asyncio.sleep(0.02)
    
    yield {"type": "done", "full_response": response}
