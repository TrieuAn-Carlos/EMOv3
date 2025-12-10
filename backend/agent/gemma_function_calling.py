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
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from core import (
    EmoState,
    initialize_context,
    format_context_block,
)
from memory import query_memory, format_memories_for_context
from agent.tools import get_all_tools


# =============================================================================
# SOCRATIC TEACHING (STUDY MODE) PROMPTS
# =============================================================================

# Simple system prompt matching Colab notebook exactly
def build_socratic_system_prompt(problem: str, analysis: str) -> str:
    """Build the system prompt for Socratic teaching - matches Colab notebook."""
    return f"""You are a Socratic teacher, please guide me to solve the problem with heuristic questions based on the following information.

[Problem]
{problem}

[Analysis]
{analysis}"""


def build_first_study_message(system_prompt: str, student_input: str) -> str:
    """Build first message with system prompt included - matches Colab notebook."""
    return f"{system_prompt}\n\n[Student]: {student_input}"


async def solve_problem_for_teaching(problem: str) -> Dict[str, str]:
    """
    Solve a problem using NORMAL Gemma 3 27B (via Gemini API).
    This separates the "solving" from the "teaching" - letting the base model
    analyze the problem, then Emo uses that analysis for Socratic teaching.
    """
    from core.llm import get_llm
    
    print("\n" + "="*70)
    print("🧠🧠🧠 SOLVER: NORMAL GEMMA 3 27B (via Gemini API) 🧠🧠🧠")
    print("="*70)
    print(f"📥 INPUT PROBLEM:\n{problem}")
    print("-"*70)
    
    # Always use Gemini (normal Gemma 3 27B) for solving - NOT the fine-tuned Emo
    solver_llm = get_llm(provider="gemini")
    
    solver_prompt = f"""Giải bài toán sau một cách ngắn gọn.

[Problem]
{problem}

Trả lời theo format:
[Answer]
(đáp án ngắn gọn)

[Analysis]
(các bước giải chính)
"""
    print(f"📤 SOLVER PROMPT:\n{solver_prompt}")
    print("-"*70)
    
    try:
        loop = asyncio.get_event_loop()
        # Add 60s timeout to prevent infinite hang
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: solver_llm.invoke([HumanMessage(content=solver_prompt)])
            ),
            timeout=60.0
        )
        print("✅ Normal Gemma 3 27B solved the problem successfully")
    except asyncio.TimeoutError:
        print("❌ SOLVER TIMEOUT after 60s")
        print("="*70 + "\n")
        return {"answer": "Timeout", "analysis": f"Bài toán: {problem}"}
    
    # Parse the response to extract Answer and Analysis
    response_text = response.content.strip()
    print(f"📨 RAW SOLVER RESPONSE:\n{response_text}")
    print("-"*70)
    
    # Extract answer
    answer = ""
    analysis = ""
    
    if "[Answer]" in response_text and "[Analysis]" in response_text:
        parts = response_text.split("[Analysis]")
        answer_part = parts[0].replace("[Answer]", "").strip()
        analysis_part = parts[1].strip() if len(parts) > 1 else ""
        answer = answer_part
        analysis = analysis_part
        print("✅ Parsed [Answer] and [Analysis] tags successfully")
    else:
        # Fallback: use entire response as analysis
        analysis = response_text
        # Try to extract a short answer from the end
        lines = response_text.strip().split("\n")
        answer = lines[-1] if lines else "Xem phân tích"
        print("⚠️ No [Answer]/[Analysis] tags found, using fallback parsing")
    
    print(f"📊 PARSED ANSWER:\n{answer}")
    print(f"📊 PARSED ANALYSIS:\n{analysis}")
    print("="*70)
    print("🎯 Analysis ready → Now feeding to Emo for Socratic teaching...")
    print("="*70 + "\n")
    
    return {"answer": answer, "analysis": analysis}


async def get_gemma_guidance(
    problem: str, 
    solution: str, 
    student_message: str, 
    conversation_history: str = ""
) -> str:
    """
    Get real-time guidance from Gemma 3 27B for each student turn.
    
    This makes Gemma act as a "teaching advisor" - analyzing the student's
    response and providing strategic thoughts for Emo to use.
    """
    from core.llm import get_llm
    
    print("\n" + "="*70)
    print("🎯🎯🎯 GUIDE: GEMMA 3 27B TEACHING ADVISOR 🎯🎯🎯")
    print("="*70)
    print(f"📥 PROBLEM: {problem[:100]}...")
    print(f"📥 STUDENT SAYS: {student_message}")
    print("-"*70)
    
    guide_llm = get_llm(provider="gemini")
    
    guide_prompt = f"""You are a teaching advisor specializing in intuitive teaching methods. Based on the following information, provide concise guidance for the AI teacher to help the student deeply understand the problem in a natural way.

[Problem]
{problem}

[Correct Solution]
{solution}

[Conversation History]
{conversation_history if conversation_history else "(This is the first message)"}

[Student Just Said]
{student_message}

Analyze and provide guidance focusing on:
1. Student's current understanding: What is the student thinking? Do they grasp the core concept? Are they confused about the fundamental nature of the problem? (DO NOT just list steps, but focus on whether the student has captured the main idea)

2. How to help the student discover on their own: Instead of giving formulas or next steps, suggest:
   - Guiding questions that help the student realize connections themselves
   - Real-world examples or analogies to help the student visualize the problem
   - Ways to help the student discover patterns or principles themselves
   - "Why" questions to help the student understand deeper reasoning

3. Building intuition: Suggest ways to help the student naturally sense the problem, such as:
   - Comparing with what the student already knows
   - Explaining through images or concrete real-life examples
   - Helping the student feel "why this is correct" rather than just remembering "how to do it"

4. Next guidance: Instead of just saying "what's the next step", suggest how the teacher can ask questions so the student figures out the direction themselves, or provide a new perspective to help the student see the problem more clearly. However, when the student provides the final answer, signal that the problem is complete and solved. When there are follow-up questions, don't ask anything more and conclude unless the student asks to continue.

AVOID: Don't just list solution steps or formulas. Focus on helping the student UNDERSTAND and FEEL the problem.

Respond concisely in 4-6 lines, focusing on how to help the student understand intuitively and guide them to find the answer themselves."""

    print(f"📤 GUIDE PROMPT:\n{guide_prompt}")
    print("-"*70)
    
    try:
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: guide_llm.invoke([HumanMessage(content=guide_prompt)])
            ),
            timeout=30.0
        )
        guidance = response.content.strip()
        print(f"✅ GEMMA GUIDANCE:\n{guidance}")
        print("="*70 + "\n")
        return guidance
    except asyncio.TimeoutError:
        print("❌ GUIDE TIMEOUT after 30s")
        print("="*70 + "\n")
        return "Tiếp tục hướng dẫn học sinh với câu hỏi gợi mở."
    except Exception as e:
        print(f"❌ GUIDE ERROR: {e}")
        print("="*70 + "\n")
        return "Tiếp tục hướng dẫn học sinh với câu hỏi gợi mở."


# =============================================================================
# HYBRID DUAL-MODEL ARCHITECTURE
# Gemini 2.5 Flash (Orchestrator) → Emo (Responder)
# =============================================================================

async def orchestrate_with_gemini(
    user_message: str,
    context_state: EmoState,
    memory_context: str = "",
    conversation_history: str = ""
) -> Dict:
    """
    Step 1: Gemini decides if tools are needed and executes them.
    Returns tool results for Emo to use in response.
    """
    from core.llm import get_llm
    
    print("\n" + "="*70)
    print("🎯🎯🎯 ORCHESTRATOR: GEMINI 2.5 FLASH 🎯🎯🎯")
    print("="*70)
    print(f"📥 USER: {user_message}")
    print("-"*70)
    
    orchestrator = get_llm(provider="gemini")
    tools = get_all_tools()
    tools_map = {tool.name: tool for tool in tools}
    
    # Build orchestrator prompt
    function_defs = build_function_definitions()
    context_block = format_context_block(context_state)
    
    prompt = f"""You are a tool orchestrator. Decide if tools are needed for this request.
The user may speak in Vietnamese or English - understand both languages.

AVAILABLE TOOLS:
{function_defs}

CONTEXT:
{context_block}

{f"MEMORY: {memory_context}" if memory_context else ""}
{f"HISTORY: {conversation_history}" if conversation_history else ""}

USER REQUEST: {user_message}

VIETNAMESE KEYWORDS FOR TOOL MATCHING:
- "tạo buổi học", "bắt đầu học", "cho con học", "mở session" → create_study_session
- "học xong", "hoàn thành", "xong rồi" → complete_study_session  
- "báo cáo", "kết quả", "làm thế nào" → get_study_report
- "dãy số", "cấp số cộng", "cấp số nhân", "chuỗi" → topic: Sequences and Series

INSTRUCTIONS:
- If a tool is needed, output ONLY: {{"name": "tool_name", "parameters": {{...}}}}
- If NO tool is needed, output ONLY: {{"name": "none", "parameters": {{}}}}
- Extract topic from user's message (keep original language or translate appropriately)
- Do NOT include any other text."""

    print(f"📤 ORCHESTRATOR PROMPT:\n{prompt[:500]}...")
    
    try:
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: orchestrator.invoke([HumanMessage(content=prompt)])),
            timeout=30.0
        )
        response_text = response.content.strip()
        print(f"📨 ORCHESTRATOR RESPONSE: {response_text}")
        
        # Parse tool call
        tool_call = parse_function_call(response_text)
        
        if tool_call and tool_call.get("name") != "none":
            func_name = tool_call["name"]
            print(f"✅ Tool needed: {func_name}")
            
            if func_name in tools_map:
                print(f"🔧 Executing tool: {func_name} with params: {tool_call.get('parameters', {})}")
                try:
                    result = execute_function(tool_call, tools_map)
                    print(f"📦 Tool result: {result[:200]}...")
                except Exception as e:
                    print(f"❌ Tool execution ERROR: {e}")
                    import traceback
                    print(traceback.format_exc())
                    result = f"Tool error: {str(e)}"
                print(f"✅ Tool execution complete, returning to main flow...")
                return {"tool_called": func_name, "tool_result": result, "thinking": response_text}
            else:
                print(f"❌ Tool '{func_name}' not found in tools_map!")
        
        print("💬 No tool needed")
        return {"tool_called": None, "tool_result": None, "thinking": response_text}
        
    except asyncio.TimeoutError:
        print("❌ ORCHESTRATOR TIMEOUT")
        return {"tool_called": None, "tool_result": None, "thinking": "timeout"}
    except Exception as e:
        print(f"❌ ORCHESTRATOR ERROR: {e}")
        return {"tool_called": None, "tool_result": None, "thinking": str(e)}


async def generate_emo_response(
    user_message: str,
    tool_result: Optional[str] = None,
    tool_name: Optional[str] = None,
    context_state: EmoState = None,
    memory_context: str = "",
    conversation_history: str = ""
) -> str:
    """
    Step 2: Emo generates natural Vietnamese response using tool results as context.
    """
    from core.llm import get_llm
    
    print("\n" + "="*70)
    print("🤖🤖🤖 RESPONDER: EMO 🤖🤖🤖")
    print("="*70)
    
    emo = get_llm()  # Default = LitGPT/Emo
    
    context_block = format_context_block(context_state) if context_state else ""
    
    prompt = f"""You are Emo, a friendly Vietnamese AI assistant.

{f"CONTEXT: {context_block}" if context_block else ""}
{f"MEMORY: {memory_context}" if memory_context else ""}
{f"HISTORY: {conversation_history}" if conversation_history else ""}

USER: {user_message}
"""

    if tool_result:
        prompt += f"""
TOOL USED: {tool_name}
TOOL RESULT:
{tool_result}

Based on the tool result above, provide a helpful response to the user.
"""
    
    prompt += """
RULES:
- Respond naturally in Vietnamese
- Be concise and friendly
- Use emojis sparingly 😊
- Format with Markdown if helpful"""

    print(f"📤 EMO PROMPT:\n{prompt[:400]}...")
    
    try:
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: emo.invoke([HumanMessage(content=prompt)])),
            timeout=60.0
        )
        result = response.content.strip()
        print(f"✅ EMO RESPONSE: {result[:200]}...")
        print("="*70 + "\n")
        return result
    except asyncio.TimeoutError:
        print("❌ EMO TIMEOUT")
        return "Xin lỗi, mình đang bận. Thử lại nhé! 😅"
    except Exception as e:
        print(f"❌ EMO ERROR: {e}")
        return f"Có lỗi xảy ra: {str(e)[:50]}"


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
        from core.llm import get_llm
        _gemma_llm = get_llm()
        print(f"✅ LLM initialized for function calling")

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
    max_iterations: int = 5,
    mode: Optional[str] = None
) -> Dict:
    """
    Chat with Gemma using manual function calling.

    Args:
        user_message: User's message
        session_id: Session ID for history
        db: Database session
        max_iterations: Maximum function calling iterations
        mode: Optional mode ('study' for Socratic teaching)

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
        # Initialize context
        global _gemma_context_state
        if _gemma_context_state is None:
            _gemma_context_state = initialize_context()

        # Load session history from database
        session_history_str = ""
        if session_id and db:
            try:
                from agent.agent import get_session_messages
                history_messages = get_session_messages(session_id, db)
                if history_messages:
                    # Format history as conversation (no truncation for debug)
                    history_lines = []
                    for msg in history_messages[-10:]:  # Last 10 messages for context
                        role = "User" if msg["role"] == "user" else "Emo"
                        content = msg["content"]  # Full content, no truncation
                        history_lines.append(f"{role}: {content}")
                    session_history_str = "\n".join(history_lines)
                    print(f"📚 Loaded {len(history_messages)} messages from session history")
                    print(f"📚 History content:\n{session_history_str}")
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

        # =====================================================================
        # STUDY MODE: Socratic Teaching (matching Colab notebook exactly)
        # Auto-detect: if session has study_context, use study mode automatically
        # =====================================================================
        from services.session_service import SessionService
        service = SessionService(db) if db else None
        
        # Check if session has study_context (auto-detect study mode)
        effective_mode = mode
        study_context = None
        if session_id and service and not mode:
            study_context = service.get_study_context(session_id)
            if study_context:
                effective_mode = "study"
                print(f"📚 Auto-detected study mode from existing session context")
        
        if effective_mode == "study":
            print(f"\n{'='*60}")
            print(f"📚📚📚 STUDY MODE ACTIVE 📚📚📚")
            print(f"{'='*60}\n")
            try:
                # Use Emo LLM for Socratic interactions
                llm = get_gemma_llm()
                # Get study_context if not already loaded
                if study_context is None and session_id and service:
                    study_context = service.get_study_context(session_id)
                
                if study_context is None:
                    # First message - solve the problem using normal Gemma 3 27B
                    print("📚 Study mode: Solving problem with normal Gemma 3 27B first...")
                    solved = await solve_problem_for_teaching(user_message)
                    print(f"📚 Study mode: Solution = {solved['analysis'][:200]}...")
                    print(f"📚 Now Emo will use this analysis for Socratic teaching...")
                    
                    # Build system prompt (matching Colab exactly)
                    system_prompt = build_socratic_system_prompt(user_message, solved["analysis"])
                    
                    # Save study context (just problem + analysis, no [Answer])
                    if session_id:
                        print(f"📚 Saving study context - problem: {user_message[:100]}...")
                        print(f"📚 Saving study context - analysis: {solved['analysis']}")
                        service.save_study_context(session_id, user_message, solved["analysis"])
                    
                    # For first response, we don't have student input yet
                    # Just ask Emo to start guiding (like Colab "Session started")
                    first_prompt = f"{system_prompt}\n\nPlease greet the student and ask the first guiding question to help them solve this problem."
                    
                    print("📚 Study mode: Generating first guiding question...")
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: llm.invoke([HumanMessage(content=first_prompt)])
                    )
                    raw_response = response.content
                    result["response"] = raw_response
                    print(f"📚 Study mode first response (raw): {raw_response}")
                    
                else:
                    # Follow-up message - continue Socratic dialogue WITH Gemma guidance
                    print("📚 Study mode: Continuing Socratic dialogue...")
                    
                    # Get stored problem and analysis
                    problem = study_context.get("problem", "")
                    analysis = study_context.get("solution", "")
                    
                    # DEBUG: Show what we loaded
                    print(f"📚 Study context loaded:")
                    print(f"📚   Problem: {problem}")
                    print(f"📚   Analysis/Solution: {analysis}")
                    
                    # Build conversation history string for Gemma guide
                    conv_history_str = ""
                    if session_id and db:
                        try:
                            from agent.agent import get_session_messages
                            history = get_session_messages(session_id, db)
                            history_lines = []
                            for msg in history[-6:]:  # Last 6 messages for context
                                role = "Học sinh" if msg["role"] == "user" else "Emo"
                                history_lines.append(f"{role}: {msg['content']}")
                            conv_history_str = "\n".join(history_lines)
                        except Exception as e:
                            print(f"⚠️ History load for guide: {e}")
                    
                    # 🎯 GET REAL-TIME GUIDANCE FROM GEMMA 3 27B
                    guidance = await get_gemma_guidance(
                        problem=problem,
                        solution=analysis,
                        student_message=user_message,
                        conversation_history=conv_history_str
                    )
                    
                    # Build enhanced system prompt WITH Gemma's guidance
                    system_prompt = f"""You are a Socratic teacher, please guide me to solve the problem with heuristic questions based on the following information.

[Problem]
{problem}

[Analysis]
{analysis}

[Real-time Teaching Guidance from Advisor]
{guidance}

Use the guidance above to craft your response. Ask guiding questions, don't give away the answer directly."""
                    
                    print(f"📚 Enhanced system prompt with guidance:\n{system_prompt}")
                    
                    # Build messages list
                    messages = []
                    
                    # Load session history
                    if session_id and db:
                        try:
                            from agent.agent import get_session_messages
                            history = get_session_messages(session_id, db)
                            
                            print(f"📚 Study mode: Loading {len(history)} messages from history")
                            for i, msg in enumerate(history):
                                print(f"📚 History[{i}]: role={msg['role']}, content={msg['content'][:50]}...")
                            
                            first_student_seen = False
                            for msg in history:
                                if msg["role"] == "user" and not first_student_seen:
                                    messages.append({
                                        "role": "user",
                                        "content": build_first_study_message(system_prompt, msg["content"])
                                    })
                                    first_student_seen = True
                                else:
                                    messages.append({
                                        "role": "user" if msg["role"] == "user" else "model",
                                        "content": msg["content"]
                                    })
                        except Exception as e:
                            print(f"⚠️ Session history error: {e}")
                            import traceback
                            print(traceback.format_exc())
                    
                    # Add current user message
                    if len(messages) == 0:
                        messages.append({
                            "role": "user",
                            "content": build_first_study_message(system_prompt, user_message)
                        })
                    else:
                        messages.append({
                            "role": "user",
                            "content": user_message
                        })
                    
                    # Build prompt for Emo
                    prompt_parts = []
                    for msg in messages:
                        role_label = "[Student]" if msg["role"] == "user" else "[Emo]"
                        if msg == messages[0] and msg["role"] == "user":
                            prompt_parts.append(msg["content"])
                        else:
                            prompt_parts.append(f"{role_label}: {msg['content']}")
                    
                    full_prompt = "\n\n".join(prompt_parts)
                    
                    print("\n" + "="*70)
                    print("🤖🤖🤖 EMO: GENERATING SOCRATIC RESPONSE 🤖🤖🤖")
                    print("="*70)
                    print(f"📤 FULL PROMPT TO EMO:\n{full_prompt[:500]}...")
                    print("-"*70)
                    
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: llm.invoke([HumanMessage(content=full_prompt)])
                    )
                    raw_response = response.content
                    result["response"] = raw_response
                    result["prompt"] = full_prompt
                    result["guidance"] = guidance
                    
                    print(f"✅ EMO RESPONSE (raw): {raw_response}")
                    print("="*70 + "\n")
                
                result["thinking"] = "Study mode: Socratic teaching"
                
                # Save to database
                if session_id and db and result["response"]:
                    from agent.agent import save_session_message
                    save_session_message(session_id, "user", user_message, db)
                    save_session_message(session_id, "assistant", result["response"], db)
                    service.auto_generate_title_if_needed(session_id)
                
                return result
            except Exception as e:
                print(f"Study mode error: {e}")
                import traceback
                print(traceback.format_exc())
                result["error"] = str(e)
                result["response"] = "❌ Có lỗi trong chế độ học tập. Vui lòng thử lại."
                return result

        elif effective_mode == "emo_only":
            print("\n" + "="*60)
            print("🟡🟡🟡 EMO-ONLY MODE ACTIVE 🟡🟡🟡")
            print("="*60 + "\n")

            result["response"] = await generate_emo_response(
                user_message=user_message,
                tool_result=None,
                tool_name=None,
                context_state=_gemma_context_state,
                memory_context=memory_context,
                conversation_history=session_history_str
            )
            result["thinking"] = "Emo-only mode: bypassed Gemini orchestrator"

            if session_id and db and result["response"]:
                try:
                    from agent.agent import save_session_message
                    save_session_message(session_id, "user", user_message, db)
                    save_session_message(session_id, "assistant", result["response"], db)

                    # Auto-generate title after 3 messages
                    service = SessionService(db)
                    service.auto_generate_title_if_needed(session_id)
                except Exception as e:
                    print(f"Database save warning (emo_only): {e}")

            return result


        # =====================================================================
        # NORMAL MODE: Hybrid Dual-Model Architecture
        # Step 1: Gemini orchestrates (decides tools)
        # Step 2: Emo responds (natural language)
        # =====================================================================
        print("\n" + "="*70)
        print("🔵🔵🔵 NORMAL MODE: HYBRID DUAL-MODEL 🔵🔵🔵")
        print("="*70)
        
        # Step 1: Gemini orchestrates
        print("📍 Step 1: Calling orchestrate_with_gemini...")
        orchestration = await orchestrate_with_gemini(
            user_message=user_message,
            context_state=_gemma_context_state,
            memory_context=memory_context,
            conversation_history=session_history_str
        )
        
        print(f"📍 Step 1 complete. Orchestration result: tool_called={orchestration.get('tool_called')}, tool_result_len={len(str(orchestration.get('tool_result', '')))}")
        
        if orchestration.get("tool_called"):
            result["tools_used"].append(orchestration["tool_called"])
            result["thinking"] = orchestration.get("thinking", "")
        
        # Step 2: Emo generates response
        print("📍 Step 2: Calling generate_emo_response...")
        result["response"] = await generate_emo_response(
            user_message=user_message,
            tool_result=orchestration.get("tool_result"),
            tool_name=orchestration.get("tool_called"),
            context_state=_gemma_context_state,
            memory_context=memory_context,
            conversation_history=session_history_str
        )
        print(f"📍 Step 2 complete. Response length: {len(result.get('response', ''))}")

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
    mode: Optional[str] = None,
    debug: bool = False
) -> AsyncGenerator[dict, None]:
    """Stream chat response from Gemma."""
    result = await chat_with_gemma(user_message, session_id=session_id, db=db, mode=mode)

    # Stream tools
    for tool in result.get("tools_used", []):
        yield {"type": "tool", "name": tool}

    # Stream response
    response = result.get("response", "")
    chunk_size = 20
    for i in range(0, len(response), chunk_size):
        yield {"type": "text", "content": response[i:i+chunk_size]}
        await asyncio.sleep(0.02)

    # Build debug info if requested
    debug_info = None
    if debug:
        debug_parts = []
        if result.get("thinking"):
            debug_parts.append(f"=== THINKING ===\n{result['thinking']}")
        if result.get("tools_used"):
            debug_parts.append(f"=== TOOLS USED ===\n{', '.join(result['tools_used'])}")
        if result.get("prompt"):
            debug_parts.append(f"=== PROMPT ===\n{result['prompt']}")
        debug_info = "\n\n".join(debug_parts) if debug_parts else "No debug data available"

    done_chunk = {"type": "done", "full_response": response}
    if debug_info:
        done_chunk["debug_info"] = debug_info
    
    yield done_chunk
