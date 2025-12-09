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
        "description": "Get detailed content of a specific email by index number",
        "parameters": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "description": "The index number of the email from search results (1-based)"
                }
            },
            "required": ["index"]
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
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days to look ahead (default: 7)",
                    "default": 7
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_news",
        "description": "Get current news headlines on a specific topic",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic: 'tech', 'ai', 'world', 'vietnam', or 'general'",
                    "default": "general"
                }
            },
            "required": []
        }
    },
    {
        "name": "read_webpage",
        "description": "Read and extract text content from a webpage URL",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The webpage URL to read"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "list_tasks",
        "description": "List all tasks/todos",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "add_task",
        "description": "Add a new task/todo",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Task description"
                }
            },
            "required": ["task"]
        }
    }
]


def build_gemma_system_prompt(context_state: EmoState) -> str:
    """Build system prompt with function calling instructions for Gemma.
    
    Based on official guide: https://ai.google.dev/gemma/docs/capabilities/function-calling
    """
    context_block = format_context_block(context_state)
    
    tools_json = json.dumps(TOOL_DEFINITIONS, indent=2)
    
    # Follow EXACT format from Google's documentation
    return f"""Bạn là Emo, trợ lý AI cá nhân.

{context_block}

You have access to functions. If you decide to invoke any of the function(s), you MUST put it in the format of
{{"name": function name, "parameters": dictionary of argument name and its value}}

You SHOULD NOT include any other text in the response if you call a function

{tools_json}"""


# =============================================================================
# GEMMA AGENT CLASS
# =============================================================================

class GemmaAgent:
    """Gemma 3 27B Agent with manual function calling support."""
    
    def __init__(self, model: str = "gemma-3-27b-it"):
        """Initialize Gemma agent.
        
        IMPORTANT: Gemma does NOT support native function calling via API.
        We use manual prompt engineering per: https://ai.google.dev/gemma/docs/capabilities/function-calling
        
        Args:
            model: Gemma model to use (default: gemma-3-27b-it)
        """
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")
        
        from core.config import MAX_OUTPUT_TOKENS
        
        # Initialize LLM WITHOUT any tools - Gemma doesn't support function calling API
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            api_key=GEMINI_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS,
            # DO NOT add tools parameter - Gemma doesn't support it
        )
        
        self.context_state = initialize_context()
        self.system_prompt = build_gemma_system_prompt(self.context_state)
        self.conversation_history: List[Dict[str, str]] = []
        
        print(f"✅ Gemma Agent initialized: {model} (manual function calling mode)")
    
    def parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from model output.
        
        Gemma outputs: {"name": "tool_name", "parameters": {...}}
        per official documentation.
        
        Args:
            text: Model output text
            
        Returns:
            Dict with name and parameters, or None if no tool call
        """
        # Try to find JSON object matching {"name": ..., "parameters": ...}
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                
                # Check for official Gemma format
                if "name" in data and "parameters" in data:
                    return {
                        "tool_name": data["name"],
                        "parameters": data["parameters"]
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
        print(f"🤖 Gemma processing: {user_message[:50]}...")
        
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
                print(f"📡 Calling Gemma LLM (iteration {iteration})...")
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.llm.invoke(messages)
                )
                
                response_text = response.content
                print(f"📝 Gemma response: {response_text[:100]}...")
                
                # Check for tool call
                tool_call = self.parse_tool_call(response_text)
                
                if tool_call:
                    # Execute tool
                    tool_name = tool_call["tool_name"]
                    parameters = tool_call["parameters"]
                    
                    result["tools_used"].append(tool_name)
                    
                    print(f"🔧 Calling tool: {tool_name} with {parameters}")
                    
                    # Execute and get result
                    tool_result = self.execute_tool(tool_name, parameters)
                    
                    # Add tool result as system message asking for interpretation
                    messages.append(AIMessage(content=response_text))
                    messages.append(HumanMessage(
                        content=f"Tool '{tool_name}' returned:\n\n{tool_result}\n\nPhân tích kết quả và trả lời người dùng bằng tiếng Việt."
                    ))
                    
                    iteration += 1
                else:
                    # No tool call - final response
                    result["response"] = response_text.strip()
                    print(f"✅ Final response ready: {len(result['response'])} chars")
                    break
            
            except Exception as e:
                print(f"❌ Gemma error: {str(e)[:200]}")
                result["error"] = str(e)[:200]
                result["response"] = f"❌ Có lỗi: {str(e)[:100]}"
                break
        
        # Fallback if no response generated
        if not result["response"]:
            result["response"] = "Xin lỗi, tôi không tạo được câu trả lời. Vui lòng thử lại."
            print("⚠️ No response generated, using fallback")
        
        print(f"🎯 Returning result with {len(result['response'])} chars")
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
