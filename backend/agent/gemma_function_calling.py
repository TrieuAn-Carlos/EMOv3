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


def clean_response(response: str) -> str:
    """Clean response by removing tags - matches Colab notebook exactly."""
    # Remove tags exactly like Colab notebook
    for tag in ["[Student]:", "[Teacher]:", "[Emo]:", "*"]:
        if tag in response:
            response = response.split(tag)[0].strip()
    return response


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
    
    guide_prompt = f"""Bạn là cố vấn giảng dạy. Dựa vào thông tin sau, hãy đưa ra hướng dẫn ngắn gọn cho giáo viên AI.

[Bài toán]
{problem}

[Lời giải đúng]
{solution}

[Lịch sử hội thoại]
{conversation_history if conversation_history else "(Đây là tin nhắn đầu tiên)"}

[Học sinh vừa nói]
{student_message}

Hãy phân tích ngắn gọn:
1. Học sinh đang ở đâu trong quá trình giải? (bắt đầu/giữa chừng/gần xong). Hãy describe vị trí của học sinh trong quá trình giải. Học sinh giải đến đâu rồi? Còn thiếu bước nào?
2. Học sinh đúng hay sai? Sai ở điểm nào?
3. Có cần hint không? Nếu có thì hint gì?
4. Bước logic tiếp theo mà học sinh cần làm là gì?

Trả lời ngắn gọn trong 3-5 dòng."""

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
                    raw_response = response.content.strip()
                    result["response"] = clean_response(raw_response)
                    print(f"📚 Study mode first response (raw): {raw_response}")
                    print(f"📚 Study mode first response (cleaned): {result['response']}")
                    
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
                    raw_response = response.content.strip()
                    result["response"] = clean_response(raw_response)
                    result["prompt"] = full_prompt
                    result["guidance"] = guidance
                    
                    print(f"✅ EMO RESPONSE (raw): {raw_response}")
                    print(f"✅ EMO RESPONSE (cleaned): {result['response']}")
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


        # =====================================================================
        # NORMAL MODE: Function calling
        # =====================================================================
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
            print(f"Response: {response_text}")
            print(f"{'='*60}\n")

            conversation_history.append({
                "iteration": iteration,
                "prompt": prompt,
                "response": response_text
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
                print(f"📦 Function result: {func_result}")

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
