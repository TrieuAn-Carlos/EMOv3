"""
Gemma 3 27B Agent with Manual Function Calling
===============================================
Based on: https://ai.google.dev/gemma/docs/capabilities/function-calling
Implements manual function calling via structured JSON prompting.
"""

import json
import asyncio
from typing import Optional, Dict, List, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

from core import (
    GEMINI_API_KEY,
    TEMPERATURE,
    EmoState,
    initialize_context,
    format_context_block,
)
from memory import query_memory, format_memories_for_context


# =============================================================================
# TOOL DEFINITIONS - Structured format for Gemma
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "search_gmail",
        "description": "Search Gmail for emails matching a query",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for emails (e.g., 'from:email@example.com', 'subject:meeting')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_email",
        "description": "Get detailed content of a specific email by ID",
        "parameters": {
            "type": "object",
            "properties": {
                "email_id": {
                    "type": "string",
                    "description": "The ID of the email to retrieve"
                }
            },
            "required": ["email_id"]
        }
    },
    {
        "name": "search_calendar",
        "description": "Search Google Calendar for events",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for calendar events"
                },
                "time_min": {
                    "type": "string",
                    "description": "Start time for search (ISO format)"
                },
                "time_max": {
                    "type": "string",
                    "description": "End time for search (ISO format)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the web for information using DuckDuckGo",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]


def build_gemma_system_prompt(context_state: EmoState) -> str:
    """Build system prompt with function calling instructions for Gemma."""
    context_block = format_context_block(context_state)
    
    tools_json = json.dumps(TOOL_DEFINITIONS, indent=2)
    
    return f"""Bạn là Emo, trợ lý AI cá nhân thông minh với khả năng gọi các công cụ (tools).

{context_block}

## AVAILABLE TOOLS

{tools_json}

## FUNCTION CALLING INSTRUCTIONS

Khi bạn cần gọi một tool để lấy thông tin:

1. Output JSON object với format CHÍNH XÁC này:
```json
{{
  "thought": "Giải thích ngắn gọn tại sao cần gọi tool này",
  "tool_name": "tên_tool",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
```

2. Sau khi nhận kết quả từ tool, phân tích và trả lời người dùng bằng ngôn ngữ tự nhiên

3. Nếu cần gọi nhiều tools, gọi từng cái một và đợi kết quả

## QUY TẮC

1. TRẢ LỜI NGẮN GỌN - không lặp lại câu hỏi
2. CHỈ GỌI TOOL khi thực sự cần dữ liệu mới
3. EMAIL: Gọi search_gmail → hiển thị danh sách → user chọn số → get_email
4. FORMAT: Markdown, emoji vừa phải 😊
5. LUÔN output valid JSON khi gọi tool

## EXAMPLES

User: "Tìm email từ Hoa"
You: 
```json
{{
  "thought": "Cần search Gmail để tìm email từ Hoa",
  "tool_name": "search_gmail",
  "parameters": {{
    "query": "from:Hoa"
  }}
}}
```

User: "Thời tiết hôm nay"
You:
```json
{{
  "thought": "Cần search web để tìm thông tin thời tiết",
  "tool_name": "search_web",
  "parameters": {{
    "query": "thời tiết hôm nay"
  }}
}}
```"""


# =============================================================================
# GEMMA AGENT CLASS
# =============================================================================

class GemmaAgent:
    """Gemma 3 27B Agent with manual function calling support."""
    
    def __init__(self, model: str = "gemma-3-27b-it"):
        """Initialize Gemma agent.
        
        Args:
            model: Gemma model to use (default: gemma-3-27b-it)
        """
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")
        
        from core.config import MAX_OUTPUT_TOKENS
        
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            api_key=GEMINI_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        
        self.context_state = initialize_context()
        self.system_prompt = build_gemma_system_prompt(self.context_state)
        self.conversation_history: List[Dict[str, str]] = []
        
        print(f"✅ Gemma Agent initialized: {model}")
    
    def parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from model output.
        
        Args:
            text: Model output text
            
        Returns:
            Dict with tool_name and parameters, or None if no tool call
        """
        # Try to extract JSON from markdown code blocks
        if "```json" in text:
            try:
                json_str = text.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_str)
                
                if "tool_name" in data and "parameters" in data:
                    return {
                        "tool_name": data["tool_name"],
                        "parameters": data["parameters"],
                        "thought": data.get("thought", "")
                    }
            except (json.JSONDecodeError, IndexError):
                pass
        
        # Try to find JSON object directly
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                
                if "tool_name" in data and "parameters" in data:
                    return {
                        "tool_name": data["tool_name"],
                        "parameters": data["parameters"],
                        "thought": data.get("thought", "")
                    }
        except json.JSONDecodeError:
            pass
        
        return None
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Execute a tool and return result.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            
        Returns:
            Tool execution result as string
        """
        try:
            from agent.tools import get_all_tools
            tools = {t.name: t for t in get_all_tools()}
            
            if tool_name not in tools:
                return f"❌ Tool '{tool_name}' not found. Available: {list(tools.keys())}"
            
            tool = tools[tool_name]
            result = tool.invoke(parameters)
            return str(result)
        
        except Exception as e:
            return f"❌ Tool execution error: {str(e)[:200]}"
    
    async def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """Process user message with function calling support.
        
        Args:
            user_message: User's message
            session_id: Optional session ID for context
            max_iterations: Max number of tool calls per message
            
        Returns:
            Dict with response, tools_used, and thinking
        """
        result = {
            "response": "",
            "tools_used": [],
            "thinking": "",
            "error": None
        }
        
        # Query memory for context
        memories = []
        simple_greetings = ["chào", "hi", "hello", "hey", "xin chào"]
        is_simple = any(g in user_message.lower() for g in simple_greetings) and len(user_message) < 20
        
        if not is_simple:
            try:
                memories = query_memory(user_message, n_results=2)
            except Exception as e:
                print(f"Memory query warning: {e}")
        
        # Build context
        context_parts = []
        if memories:
            mem_formatted = format_memories_for_context(memories)
            if mem_formatted:
                context_parts.append(f"[Bộ nhớ liên quan]:\n{mem_formatted}")
        
        context_parts.append(f"[User]: {user_message}")
        full_input = "\n\n".join(context_parts)
        
        # Initial message with system prompt
        messages = [
            HumanMessage(content=self.system_prompt + "\n\n" + full_input)
        ]
        
        # Conversation loop with tool calling
        iteration = 0
        
        while iteration < max_iterations:
            try:
                # Call LLM
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.llm.invoke(messages)
                )
                
                response_text = response.content
                
                # Check for tool call
                tool_call = self.parse_tool_call(response_text)
                
                if tool_call:
                    # Execute tool
                    tool_name = tool_call["tool_name"]
                    parameters = tool_call["parameters"]
                    thought = tool_call.get("thought", "")
                    
                    result["tools_used"].append(tool_name)
                    if thought:
                        result["thinking"] += f"{thought}\n"
                    
                    print(f"🔧 Calling tool: {tool_name} with {parameters}")
                    
                    # Execute and get result
                    tool_result = self.execute_tool(tool_name, parameters)
                    
                    # Add to conversation
                    messages.append(AIMessage(content=response_text))
                    messages.append(HumanMessage(
                        content=f"[Tool Result from {tool_name}]\n\n{tool_result}\n\nHãy phân tích kết quả này và trả lời người dùng."
                    ))
                    
                    iteration += 1
                else:
                    # No tool call - this is the final response
                    # Clean up JSON artifacts if any
                    final_response = response_text
                    if "```json" in final_response:
                        # Remove JSON blocks from final response
                        parts = final_response.split("```json")
                        final_response = parts[0].strip()
                    
                    result["response"] = final_response.strip()
                    break
            
            except Exception as e:
                result["error"] = str(e)[:200]
                result["response"] = f"❌ Có lỗi: {str(e)[:100]}"
                break
        
        # Fallback if no response generated
        if not result["response"]:
            result["response"] = "Xin lỗi, tôi không tạo được câu trả lời. Vui lòng thử lại."
        
        return result


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_gemma_agent: Optional[GemmaAgent] = None


def get_gemma_agent(force_recreate: bool = False) -> GemmaAgent:
    """Get or create global Gemma agent instance.
    
    Args:
        force_recreate: Force create new agent
        
    Returns:
        GemmaAgent instance
    """
    global _gemma_agent
    
    if _gemma_agent is None or force_recreate:
        _gemma_agent = GemmaAgent()
    
    return _gemma_agent
