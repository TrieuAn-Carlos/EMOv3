"""
EMO2 - Chat Engine
==================
Core chat logic with 3-phase architecture: Classify → Execute → Respond.
"""

import re
import time
from typing import Tuple, List, Dict

import streamlit as st

from config import GEMINI_MODEL, get_gemini_model
from prompts import build_dynamic_system_prompt
from task_manager import get_smart_reminders
from quiz import generate_quiz


def classify_query(message: str) -> Tuple[str, List[str]]:
    """
    Fast keyword-based router to determine query type and needed tools.
    
    Returns:
        (query_type, list_of_tools_to_run)
    """
    msg_lower = message.lower()
    
    # Keyword groups
    email_keywords = ['email', 'mail', 'gmail', 'inbox', 'message from', 'sent by']
    attachment_keywords = ['attachment', 'attached', 'file', 'document', 'pdf', 'doc']
    todo_keywords = ['todo', 'task', 'remind', 'reminder', 'add to', 'schedule']
    todo_check = ['what are my', 'show me my', 'list my', 'my tasks', 'my todos']
    web_keywords = ['website', 'webpage', 'url', 'http', 'www', 'read this', 'check this link']
    youtube_keywords = ['youtube', 'video', 'watch', 'yt.com', 'youtu.be']
    news_keywords = ['news', 'headlines', "what's happening", 'current events']
    quiz_keywords = ['quiz', 'test me', 'test my', 'quizz', 'generate quiz', 'make quiz', 'create quiz']
    memory_keywords = ['remember', 'recall', 'what did', 'previously', 'earlier', 'you told me']
    save_keywords = ['save this', 'remember this', 'note this', 'store this']
    greeting_keywords = ['hi', 'hello', 'hey', 'how are you', "what's up", 'thanks', 'thank you']
    
    tools_needed = []
    query_type = 'chat'
    
    # Simple greetings
    if any(msg_lower.strip().startswith(g) or msg_lower.strip() == g for g in greeting_keywords):
        return ('simple_chat', [])
    
    # Quiz generation
    if any(kw in msg_lower for kw in quiz_keywords):
        return ('quiz', [])
    
    # Attachment analysis
    analyze_keywords = ['analyze', 'summarize', 'read the', 'show the', "what's in the", 'open the']
    if any(kw in msg_lower for kw in attachment_keywords):
        if any(kw in msg_lower for kw in analyze_keywords) or 'all' in msg_lower:
            tools_needed.append('analyze_attachment')
            query_type = 'attachment'
        elif any(kw in msg_lower for kw in email_keywords):
            tools_needed.append('quick_gmail_search')
            query_type = 'email'
    elif any(kw in msg_lower for kw in email_keywords):
        tools_needed.append('quick_gmail_search')
        query_type = 'email'
    
    # Todos
    if any(kw in msg_lower for kw in todo_keywords):
        if any(kw in msg_lower for kw in ['add', 'create', 'new', 'set']):
            tools_needed.append('add_todo')
        elif any(kw in msg_lower for kw in ['done', 'complete', 'finish', 'mark']):
            tools_needed.append('complete_todo')
        else:
            tools_needed.append('get_todos')
        query_type = 'todo'
    elif any(kw in msg_lower for kw in todo_check):
        tools_needed.append('get_todos')
        query_type = 'todo'
    
    # Web content
    if any(kw in msg_lower for kw in youtube_keywords):
        tools_needed.append('watch_youtube')
        query_type = 'web'
    elif any(kw in msg_lower for kw in web_keywords) or 'http' in msg_lower:
        tools_needed.append('read_web_page')
        query_type = 'web'
    elif any(kw in msg_lower for kw in news_keywords):
        tools_needed.append('get_news_headlines')
        query_type = 'web'
    
    # Memory
    if any(kw in msg_lower for kw in save_keywords):
        tools_needed.append('save_long_term_memory')
        query_type = 'memory'
    elif any(kw in msg_lower for kw in memory_keywords):
        tools_needed.append('search_memory')
        query_type = 'memory'
    
    # Questions might need memory
    if not tools_needed and '?' in message:
        query_type = 'question'
    
    return (query_type, tools_needed)


def select_model_for_task(query_type: str, has_tools: bool) -> str:
    """Select the model for the task. Unified to Gemini 2.5 Flash."""
    return GEMINI_MODEL


def prepare_tool_args(tool_name: str, user_message: str) -> dict:
    """Prepare arguments for a tool based on the user message."""
    msg_lower = user_message.lower()
    
    if tool_name in ['quick_gmail_search', 'check_gmail_and_learn', 'fetch_email_attachments', 'get_full_email']:
        query = user_message
        for prefix in ['check', 'find', 'get', 'show', 'give me', 'search for']:
            if msg_lower.startswith(prefix):
                query = user_message[len(prefix):].strip()
                break
        return {'query': query}
    
    elif tool_name == 'get_email_by_index':
        numbers = re.findall(r'\d+', user_message)
        if numbers:
            return {'index': int(numbers[0])}
        word_map = {'first': 1, '1st': 1, 'second': 2, '2nd': 2, 'third': 3, '3rd': 3}
        for word, idx in word_map.items():
            if word in msg_lower:
                return {'index': idx}
        return {'index': 1}
    
    elif tool_name == 'analyze_attachment':
        numbers = re.findall(r'\d+', user_message)
        email_idx = st.session_state.get('last_viewed_email_index', 1)
        att_idx = 1
        
        if 'attachments' in msg_lower or 'all files' in msg_lower:
            att_idx = 0
        
        if len(numbers) >= 2:
            att_idx, email_idx = int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            att_idx = int(numbers[0])
        
        return {'email_index': email_idx, 'attachment_index': att_idx}
    
    elif tool_name == 'add_todo':
        task = user_message
        for prefix in ['add', 'create', 'remind me to', 'add todo', 'add task']:
            if msg_lower.startswith(prefix):
                task = user_message[len(prefix):].strip()
                break
        return {'task': task}
    
    elif tool_name == 'complete_todo':
        numbers = re.findall(r'\d+', user_message)
        return {'task_id': int(numbers[0])} if numbers else {'task_id': 1}
    
    elif tool_name == 'get_todos':
        return {}
    
    elif tool_name == 'read_web_page':
        urls = re.findall(r'https?://\S+', user_message)
        return {'url': urls[0]} if urls else {'url': user_message}
    
    elif tool_name == 'watch_youtube':
        urls = re.findall(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+[^\s]*', user_message)
        if urls:
            return {'video_url': urls[0]}
        return {'video_url': user_message.strip()}
    
    elif tool_name == 'get_news_headlines':
        topic_urls = {
            'ai': 'https://techcrunch.com/category/artificial-intelligence/',
            'tech': 'https://techcrunch.com/',
            'world': 'https://www.bbc.com/news/world',
            'vietnam': 'https://vnexpress.net/',
        }
        for key, url in topic_urls.items():
            if key in msg_lower:
                return {'url': url}
        return {'url': 'https://news.google.com/'}
    
    elif tool_name == 'search_memory':
        return {'query': user_message}
    
    elif tool_name == 'save_long_term_memory':
        content = user_message
        for prefix in ['save', 'remember', 'note']:
            if msg_lower.startswith(prefix):
                content = user_message[len(prefix):].strip()
                break
        return {'content': content, 'category': 'user_note'}
    
    return {'query': user_message}


def get_chat_messages():
    """Get or create chat message history for Gemini."""
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    return st.session_state.chat_messages


def format_tool_args(args: dict) -> str:
    """Format tool arguments for display."""
    if not args:
        return "none"
    formatted = []
    for key, value in args.items():
        if isinstance(value, str) and len(value) > 50:
            value = value[:47] + "..."
        formatted.append(f"{key}={repr(value)}")
    return ", ".join(formatted)


def execute_tool_with_display(tool_name: str, tool_args: dict, tool_container) -> str:
    """Execute a tool and display real-time status."""
    available_tools = st.session_state.get('available_tools', {})
    
    if tool_name not in available_tools:
        return f"Error: Unknown tool '{tool_name}'"
    
    tool_func = available_tools[tool_name]
    start_time = time.time()
    
    try:
        result = tool_func(**tool_args)
        execution_time = time.time() - start_time
        
        with tool_container:
            st.markdown(f"""
<div style="font-family: monospace; font-size: 0.75rem; padding: 0.5rem; background: #0d1117; border-radius: 4px; margin: 0.25rem 0; border-left: 2px solid #3fb950;">
<span style="color: #3fb950;">done</span> · <span style="color: #8b949e;">{tool_name}</span> · <span style="color: #666;">{execution_time:.2f}s</span>
</div>
""", unsafe_allow_html=True)
        
        return str(result)
    except Exception as e:
        with tool_container:
            st.markdown(f"""
<div style="font-family: monospace; font-size: 0.75rem; padding: 0.5rem; background: #0d1117; border-radius: 4px; margin: 0.25rem 0; border-left: 2px solid #f85149;">
<span style="color: #f85149;">error</span> · <span style="color: #8b949e;">{tool_name}</span>
</div>
""", unsafe_allow_html=True)
        return f"Error: {str(e)[:100]}"


def display_tool_call_start(tool_name: str, tool_args: dict, tool_container, index: int):
    """Display a tool call in progress."""
    with tool_container:
        st.markdown(f"""
<div style="font-family: monospace; font-size: 0.75rem; padding: 0.5rem; background: #0d1117; border-radius: 4px; margin: 0.25rem 0; border-left: 2px solid #58a6ff;">
<span style="color: #58a6ff;">running</span> · <span style="color: #8b949e;">{tool_name}</span>
</div>
""", unsafe_allow_html=True)


def display_thinking(thinking_container, query_type: str, tools_needed: list, model: str, tool_results: list = None):
    """Display AI thinking process in a collapsible section."""
    with thinking_container:
        steps = [f"Understanding the request: analyzing query type..."]
        
        type_messages = {
            'simple_chat': "This is a casual/greeting message - no tools needed.",
            'email': "User is asking about emails - need to search Gmail.",
            'todo': "This is about tasks/todos - checking task manager.",
            'web': "User wants web content - fetching from internet.",
            'memory': "Looking for stored information in memory."
        }
        steps.append(type_messages.get(query_type, f"Query classified as: {query_type}"))
        
        if tools_needed:
            steps.append(f"Tools to use: {', '.join(tools_needed)}")
        
        model_name = model.split('/')[-1] if '/' in model else model
        steps.append(f"Using model: {model_name}")
        
        if tool_results:
            for tr in tool_results:
                if tr.get('result', '')[:100]:
                    steps.append(f"Got results from {tr.get('tool', 'tool')}")
        
        with st.expander("💭 Thinking...", expanded=False):
            for step in steps:
                st.markdown(f"""
<div style="font-size: 0.85rem; color: #8b949e; padding: 0.25rem 0; border-left: 2px solid #30363d; padding-left: 0.75rem; margin: 0.25rem 0;">
{step}
</div>
""", unsafe_allow_html=True)


def _convert_to_gemini_format(api_messages: list) -> list:
    """Convert OpenAI-style messages to Gemini format."""
    gemini_contents = []
    system_instruction = None
    
    for msg in api_messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        if role == 'system':
            system_instruction = content
        elif role == 'assistant':
            gemini_contents.append({'role': 'model', 'parts': [content]})
        else:
            gemini_contents.append({'role': 'user', 'parts': [content]})
    
    if system_instruction and gemini_contents:
        first = gemini_contents[0]
        if isinstance(first['parts'][0], str):
            first['parts'][0] = f"[System: {system_instruction}]\n\n{first['parts'][0]}"
    
    return gemini_contents


def chat_with_emo(user_message: str, memory_context: str = "", show_thinking: bool = False, tool_display_container=None) -> dict:
    """
    Smart 3-phase chat architecture:
    1. CLASSIFY: Fast keyword-based routing
    2. EXECUTE: Run needed tools directly
    3. RESPOND: Single AI call with all context
    """
    # Setup tools if not already done
    if 'available_tools' not in st.session_state:
        from chat_engine import setup_tools
        setup_tools()
    
    gemini_model = get_gemini_model()
    messages = get_chat_messages()
    
    result = {
        'response': '',
        'thinking': '',
        'tools_used': [],
        'tool_results': [],
        'tool_executions': []
    }
    
    thinking_container = tool_display_container if show_thinking else None
    
    try:
        # PHASE 1: CLASSIFY
        query_type, tools_needed = classify_query(user_message)
        model = select_model_for_task(query_type, len(tools_needed) > 0)
        
        # PHASE 2: EXECUTE TOOLS
        tool_context = []
        
        for tool_name in tools_needed:
            if tool_name not in st.session_state.available_tools:
                continue
            
            tool_args = prepare_tool_args(tool_name, user_message)
            result['tools_used'].append(tool_name)
            
            if tool_display_container:
                display_tool_call_start(tool_name, tool_args, tool_display_container, 0)
            
            start_time = time.time()
            tool_result = execute_tool_with_display(
                tool_name, tool_args,
                tool_display_container if tool_display_container else st.empty()
            )
            duration = time.time() - start_time
            
            result['tool_executions'].append({
                'tool': tool_name, 'args': tool_args, 'duration': duration,
                'result': tool_result[:300] if tool_result else ""
            })
            
            tool_context.append(f"[{tool_name} result]:\n{tool_result}")
        
        if show_thinking and thinking_container:
            display_thinking(thinking_container, query_type, tools_needed, model, result['tool_executions'])
        
        # PHASE 3: GENERATE RESPONSE
        context_parts = []
        
        # Recent conversation
        if messages:
            recent = messages[-8:]
            conv = [f"{'User' if m['role'] == 'user' else 'Emo'}: {m['content'][:300]}" for m in recent]
            context_parts.append(f"[Recent conversation]:\n" + "\n".join(conv))
        
        if memory_context:
            context_parts.append(f"[Relevant memories]:\n{memory_context}")
        
        if tool_context:
            context_parts.append("\n".join(tool_context))
        
        reminders = get_smart_reminders()
        if reminders:
            context_parts.append(reminders)
        
        # Build prompt
        if context_parts:
            full_prompt = f"Here is the context and tool results:\n\n{chr(10).join(context_parts)}\n\nUser message: {user_message}\n\nBased on the above context and results, provide a helpful response."
        else:
            full_prompt = user_message
        
        messages.append({"role": "user", "content": user_message})
        
        # System prompt
        if query_type == 'simple_chat':
            system_prompt = "You are Emo, a friendly AI assistant. Be warm, brief, and natural."
        else:
            system_prompt = build_dynamic_system_prompt()
        
        # API call
        api_messages = [{"role": "system", "content": system_prompt}]
        recent_history = messages[-6:] if len(messages) > 6 else messages
        for msg in recent_history:
            api_messages.append({"role": msg["role"], "content": msg["content"]})
        api_messages.append({"role": "user", "content": full_prompt})
        
        # Quiz mode
        if query_type == 'quiz':
            quiz_prompt = full_prompt + """

Generate an interactive quiz as a JSON code block. ONLY use multiple_choice and true_false types.
Output ONLY the JSON block, no other text."""
            api_messages[-1] = {"role": "user", "content": quiz_prompt}
            
            gemini_contents = _convert_to_gemini_format(api_messages)
            response = gemini_model.generate_content(gemini_contents)
            raw_response = response.text if response.text else ""
            
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
            if json_match:
                quiz_result = generate_quiz(json_match.group(1).strip())
                result['tools_used'].append('generate_quiz')
                result['response'] = quiz_result
                messages.append({"role": "assistant", "content": result['response']})
                st.session_state.chat_messages = messages
                return result
        
        gemini_contents = _convert_to_gemini_format(api_messages)
        response = gemini_model.generate_content(gemini_contents)
        raw_response = response.text if response.text else ""
        
        # Parse thinking blocks
        if '<think>' in raw_response.lower():
            think_pattern = r'<think>\s*(.*?)\s*</think>'
            think_matches = re.findall(think_pattern, raw_response, re.DOTALL | re.IGNORECASE)
            if think_matches:
                result['thinking'] = '\n'.join(think_matches).strip()
                result['response'] = re.sub(think_pattern, '', raw_response, flags=re.DOTALL | re.IGNORECASE).strip()
            else:
                result['response'] = raw_response
        else:
            result['response'] = raw_response
        
        result['response'] = re.sub(r'</?think>', '', result['response'], flags=re.IGNORECASE).strip()
        
        messages.append({"role": "assistant", "content": result['response']})
        st.session_state.chat_messages = messages
        
        return result
    
    except Exception as e:
        result['response'] = f"Sorry, I encountered an error: {str(e)}"
        return result


def setup_tools():
    """Setup available tools mapping. Must import tool functions here."""
    from gmail_tools import (
        check_gmail_and_learn, quick_gmail_search, get_email_by_index,
        analyze_attachment, fetch_email_attachments, get_full_email
    )
    from task_manager import add_todo, get_todos, complete_todo
    from web_tools import read_web_page, watch_youtube, get_news_headlines
    from quiz import generate_quiz
    import tools as memory_tools
    
    st.session_state.available_tools = {
        'check_gmail_and_learn': check_gmail_and_learn,
        'quick_gmail_search': quick_gmail_search,
        'get_email_by_index': get_email_by_index,
        'analyze_attachment': analyze_attachment,
        'fetch_email_attachments': fetch_email_attachments,
        'get_full_email': get_full_email,
        'add_todo': add_todo,
        'get_todos': get_todos,
        'complete_todo': complete_todo,
        'read_web_page': read_web_page,
        'watch_youtube': watch_youtube,
        'get_news_headlines': get_news_headlines,
        'recall_memory': memory_tools.recall_memory,
        'search_memory': memory_tools.search_memory,
        'save_short_term_memory': memory_tools.save_short_term_memory,
        'save_long_term_memory': memory_tools.save_long_term_memory,
        'save_project_memory': memory_tools.save_project_memory,
        'query_short_term': memory_tools.query_short_term,
        'query_long_term': memory_tools.query_long_term,
        'query_project': memory_tools.query_project,
        'list_all_projects': memory_tools.list_all_projects,
        'update_long_term_memory': memory_tools.update_long_term_memory,
        'generate_quiz': generate_quiz,
    }
