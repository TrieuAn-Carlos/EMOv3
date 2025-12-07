"""
EMO2 - LangGraph ReAct Agent
============================
Modern agentic architecture using Gemini native function calling.
Replaces keyword-based routing with semantic tool selection.

Author: EMO Team
Version: 3.0
"""

import os
from typing import Annotated, TypedDict, List, Dict, Any
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

import streamlit as st

from config import GEMINI_API_KEY, GEMINI_MODEL, TEMPERATURE


# =============================================================================
# AGENT STATE
# =============================================================================

class AgentState(TypedDict):
    """State for the ReAct agent."""
    messages: Annotated[list, add_messages]
    context: str  # Memory context, user identity, etc.


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def get_agent_system_prompt() -> str:
    """Build the system prompt for the agent."""
    from state import get_current_datetime
    
    current_time, current_date = get_current_datetime()
    
    return f"""Bạn là Emo, trợ lý AI cá nhân siêu vui vẻ và thông minh!

## Ngữ cảnh hiện tại
- Ngày: {current_date}
- Giờ: {current_time}

## Tính cách Emo
- VUI VẺ, năng động, hoạt bát như đang nhắn tin với bạn thân
- Hay nói chuyện, thân thiện, hào hứng nhưng VẪN SÚCSTÍCH
- Dùng ngôn ngữ trẻ trung, gần gũi (có thể dùng từ như "nè", "hen", "á")
- Thỉnh thoảng dùng emoji để thể hiện cảm xúc 😄✨

## QUAN TRỌNG: Ngôn ngữ
**LUÔN LUÔN trả lời bằng tiếng Việt**, dù người dùng hỏi bằng tiếng Anh hay ngôn ngữ khác.

## Công cụ có sẵn
- **Email**: Tìm Gmail, đọc email, phân tích file đính kèm
- **Lịch**: Xem sự kiện, thêm lịch hẹn
- **Tasks**: Thêm, xem, hoàn thành việc cần làm
- **Bộ nhớ**: Lưu và nhớ thông tin cá nhân
- **Web**: Đọc trang web, YouTube, tin tức
- **Quiz**: Tạo câu đố học tập

## Quy tắc
1. Gọi tools khi cần - AI tự quyết định
2. Với email, LUÔN lấy dữ liệu mới nhất
3. Với tasks có thời gian, trích xuất deadline tự nhiên
4. Trả lời ngắn gọn, đi vào trọng tâm

## Phong cách
- Dùng số thường 1. 2. 3.
- Markdown: **đậm**, *nghiêng*, tiêu đề
- Chào hỏi ngắn gọn, tự nhiên, vui vẻ"""


# =============================================================================
# TOOL DEFINITIONS (Enhanced docstrings for better LLM understanding)
# =============================================================================

def get_emo_tools() -> list:
    """Get all EMO tools with enhanced descriptions for LLM tool calling."""
    
    # Gmail Tools
    from gmail_tools import (
        quick_gmail_search as _quick_gmail_search,
        get_email_by_index as _get_email_by_index,
        analyze_attachment as _analyze_attachment,
    )
    
    # Task Tools  
    from task_manager import (
        add_todo as _add_todo,
        get_todos as _get_todos,
        complete_todo as _complete_todo,
    )
    
    # Web Tools
    from web_tools import (
        read_web_page as _read_web_page,
        watch_youtube as _watch_youtube,
        get_news_headlines as _get_news_headlines,
    )
    
    # Memory Tools
    from tools import (
        search_memory as _search_memory,
        save_long_term_memory as _save_long_term_memory,
        query_long_term as _query_long_term,
    )
    
    # Quiz
    from quiz import generate_quiz as _generate_quiz
    
    # Calendar Tools
    from calendar_tools import (
        list_upcoming_events as _list_events,
        search_events as _search_events,
        quick_add_event as _quick_add_event,
    )
    
    # Wrap tools with enhanced docstrings
    @tool
    def search_gmail(query: str, max_results: int = 3) -> str:
        """
        Search Gmail inbox for emails matching a query.
        
        Use this for ANY email-related request:
        - "check my email" → query="is:unread" or query="newer_than:1d"
        - "email from John" → query="from:John"
        - "emails about meeting" → query="subject:meeting OR meeting"
        
        Args:
            query: Gmail search query (natural language or Gmail syntax)
            max_results: Maximum emails to return (default 3)
            
        Returns:
            Full email content including subject, sender, date, and body
        """
        return _quick_gmail_search(query, max_results)
    
    @tool
    def get_email(index: int) -> str:
        """
        Get a specific email by its index number from the last search.
        
        Use when user says "email 2", "the second one", "number 3".
        
        Args:
            index: Email number (1, 2, 3, etc.)
            
        Returns:
            Full email content
        """
        return _get_email_by_index(index)
    
    @tool
    def analyze_email_attachment(email_index: int, attachment_index: int = 1) -> str:
        """
        Read and analyze an attachment from an email.
        
        Use when user wants to read a PDF, document, or spreadsheet from an email.
        
        Args:
            email_index: Which email (1, 2, 3...)
            attachment_index: Which attachment in that email (default 1)
            
        Returns:
            Extracted text content from the attachment
        """
        return _analyze_attachment(email_index, attachment_index)
    
    @tool
    def add_task(task_description: str, deadline: str = None) -> str:
        """
        Add a new task to the todo list.
        
        Args:
            task_description: What needs to be done (without the time/date part)
            deadline: ISO datetime string if task has a deadline.
                      Extract from natural language in the user's message:
                      - "at 5pm" → today at 17:00:00
                      - "tomorrow morning" → tomorrow at 09:00:00
                      - "in 2 hours" → current time + 2 hours
                      - "next Tuesday" → next Tuesday at 09:00:00
                      Set to None if no deadline/time mentioned.
                      Format: "YYYY-MM-DDTHH:MM:SS"
        
        Returns:
            Confirmation with task details
        """
        return _add_todo(task_description, deadline)
    
    @tool
    def list_tasks() -> str:
        """
        Get all pending tasks from the todo list.
        
        Use for "what are my tasks?", "show todos", "my to-do list".
        
        Returns:
            Numbered list of pending tasks with creation dates
        """
        return _get_todos()
    
    @tool
    def complete_task(task_number: int) -> str:
        """
        Mark a task as done by its number.
        
        Use when user says "done with task 1", "complete number 2".
        
        Args:
            task_number: Which task to complete (1, 2, 3...)
            
        Returns:
            Confirmation that task was completed
        """
        return _complete_todo(task_number)
    
    @tool
    def read_webpage(url: str) -> str:
        """
        Fetch and read content from a webpage URL.
        
        Use when user shares a link or asks to read a website.
        
        Args:
            url: Full URL starting with http:// or https://
            
        Returns:
            Extracted text content from the webpage
        """
        return _read_web_page(url)
    
    @tool
    def get_youtube_transcript(video_url: str) -> str:
        """
        Get the transcript/captions from a YouTube video.
        
        Use when user shares a YouTube link or asks about a video.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Full transcript of the video
        """
        return _watch_youtube(video_url)
    
    @tool
    def get_news(topic: str = "general") -> str:
        """
        Get current news headlines.
        
        Args:
            topic: News topic - "tech", "ai", "world", "vietnam", or "general"
            
        Returns:
            Latest news headlines
        """
        topic_urls = {
            'ai': 'https://techcrunch.com/category/artificial-intelligence/',
            'tech': 'https://techcrunch.com/',
            'world': 'https://www.bbc.com/news/world',
            'vietnam': 'https://vnexpress.net/',
            'general': 'https://news.google.com/',
        }
        url = topic_urls.get(topic.lower(), topic_urls['general'])
        return _get_news_headlines(url)
    
    @tool
    def remember_fact(fact: str, category: str = "other") -> str:
        """
        Save a personal fact to long-term memory (permanent).
        
        Categories: "identity", "preference", "relationship", "date", "skill", "other"
        
        Args:
            fact: The information to permanently remember
            category: Type of information
            
        Returns:
            Confirmation
        """
        return _save_long_term_memory(fact, category)
    
    @tool
    def recall_personal_info(query: str) -> str:
        """
        Search long-term memory for personal facts about the user.
        
        Use when user asks about previously shared personal information.
        
        Args:
            query: What to search for
            
        Returns:
            Matching personal facts
        """
        return _query_long_term(query)
    
    @tool
    def search_saved_content(query: str) -> str:
        """
        Search all saved memories including emails, webpages, and notes.
        
        Args:
            query: What to search for
            
        Returns:
            Matching saved content with relevance scores
        """
        return _search_memory(query)
    
    @tool
    def create_quiz(topic: str, num_questions: int = 5) -> str:
        """
        Generate an interactive quiz on a topic.
        
        Use when user wants to test their knowledge or learn.
        
        Args:
            topic: Subject to quiz on (e.g., "Python basics", "World War 2")
            num_questions: Number of questions (default 5)
            
        Returns:
            Interactive quiz structure
        """
        from config import get_gemini_model
        import json
        
        model = get_gemini_model()
        prompt = f"""Generate a {num_questions}-question quiz about "{topic}".
        
Return ONLY valid JSON in this format:
{{
    "title": "Quiz: {topic}",
    "questions": [
        {{
            "id": 1,
            "type": "multiple_choice",
            "question": "Question text?",
            "options": ["A", "B", "C", "D"],
            "correct": 0,
            "explanation": "Why A is correct"
        }}
    ]
}}"""
        response = model.generate_content(prompt)
        
        # Extract JSON
        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return _generate_quiz(json_match.group())
        return _generate_quiz(response.text)
    
    # Calendar Tools
    @tool
    def get_calendar_events(days: int = 7) -> str:
        """
        Get upcoming calendar events.
        
        Use for "what's on my calendar?", "my schedule", "upcoming events".
        
        Args:
            days: Number of days to look ahead (default 7)
            
        Returns:
            List of upcoming events with times
        """
        return _list_events(days)
    
    @tool
    def add_calendar_event(description: str) -> str:
        """
        Add a new event to Google Calendar using natural language.
        
        Use when user wants to schedule something:
        - "Meeting with John tomorrow at 3pm"
        - "Dentist appointment Friday 10am"
        - "Team standup every Monday 9am"
        
        Args:
            description: Natural language event description
            
        Returns:
            Confirmation with event details and calendar link
        """
        return _quick_add_event(description)
    
    @tool
    def search_calendar(query: str) -> str:
        """
        Search calendar for events matching a keyword.
        
        Use when user asks "when is my dentist appointment?", 
        "do I have a meeting with John?".
        
        Args:
            query: Search term (e.g., "dentist", "John", "team meeting")
            
        Returns:
            Matching calendar events
        """
        return _search_events(query)
    
    return [
        search_gmail,
        get_email,
        analyze_email_attachment,
        add_task,
        list_tasks,
        complete_task,
        read_webpage,
        get_youtube_transcript,
        get_news,
        remember_fact,
        recall_personal_info,
        search_saved_content,
        create_quiz,
        get_calendar_events,
        add_calendar_event,
        search_calendar,
    ]


# =============================================================================
# AGENT CREATION
# =============================================================================

def create_emo_agent():
    """Create the LangGraph ReAct agent with Gemini."""
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment")
    
    # Initialize Gemini LLM
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=TEMPERATURE,
        convert_system_message_to_human=True,  # Gemini compatibility
    )
    
    # Get tools
    tools = get_emo_tools()
    
    # Create ReAct agent with system prompt
    agent = create_react_agent(
        llm,
        tools,
        prompt=get_agent_system_prompt(),  # System prompt for personality
    )
    
    return agent


def get_emo_agent():
    """Get or create the cached EMO agent."""
    if 'emo_agent' not in st.session_state:
        st.session_state.emo_agent = create_emo_agent()
    return st.session_state.emo_agent


# =============================================================================
# MAIN CHAT FUNCTION (Replaces chat_with_emo)
# =============================================================================

def chat_with_agent(
    user_message: str,
    memory_context: str = "",
    show_thinking: bool = False,
    tool_display_container=None
) -> dict:
    """
    Process a user message through the LangGraph agent.
    
    Args:
        user_message: The user's input
        memory_context: Optional memory context to include
        show_thinking: Whether to show tool execution (for UI)
        tool_display_container: Streamlit container for tool status
        
    Returns:
        dict with 'response', 'thinking', 'tools_used'
    """
    agent = get_emo_agent()
    
    result = {
        'response': '',
        'thinking': '',
        'tools_used': [],
    }
    
    # Build input with context
    if memory_context:
        full_input = f"[Relevant context from memory]:\n{memory_context}\n\n[User message]: {user_message}"
    else:
        full_input = user_message
    
    # Get conversation history
    messages = st.session_state.get('chat_messages', [])
    
    # Convert to LangChain format
    lc_messages = []
    for msg in messages[-6:]:  # Last 6 messages for context
        if msg['role'] == 'user':
            lc_messages.append(HumanMessage(content=msg['content']))
        else:
            lc_messages.append(AIMessage(content=msg['content']))
    
    # Add current message
    lc_messages.append(HumanMessage(content=full_input))
    
    try:
        # Run agent
        agent_response = agent.invoke({"messages": lc_messages})
        
        # Extract final response
        final_messages = agent_response.get('messages', [])
        
        # Collect tool calls and final response
        thinking_parts = []
        for msg in final_messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name', 'unknown_tool')
                    result['tools_used'].append(tool_name)
                    thinking_parts.append(f"Called: {tool_name}")
                    
                    # Display in UI if container provided
                    if tool_display_container:
                        with tool_display_container:
                            st.markdown(f"""
<div style="font-family: monospace; font-size: 0.75rem; padding: 0.5rem; background: #0d1117; border-radius: 4px; margin: 0.25rem 0; border-left: 2px solid #3fb950;">
<span style="color: #3fb950;">✓</span> · <span style="color: #8b949e;">{tool_name}</span>
</div>
""", unsafe_allow_html=True)
        
        # Get the final AI message
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                content = msg.content
                # Handle structured content blocks (list of dicts with 'type': 'text')
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif isinstance(item, str):
                            text_parts.append(item)
                    result['response'] = ' '.join(text_parts)
                else:
                    result['response'] = str(content)
                break
        
        if thinking_parts:
            result['thinking'] = '\n'.join(thinking_parts)
        
    except Exception as e:
        result['response'] = f"I encountered an error: {str(e)[:200]}"
    
    return result


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing EMO Agent...")
    
    # Test cases
    tests = [
        "What's up?",
        "Check my email",
        "Add a task: meeting at 5pm",
        "What are my todos?",
    ]
    
    for test in tests:
        print(f"\n> {test}")
        result = chat_with_agent(test)
        print(f"< {result['response'][:200]}...")
        if result['tools_used']:
            print(f"  Tools: {result['tools_used']}")
