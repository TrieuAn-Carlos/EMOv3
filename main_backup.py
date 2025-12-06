"""
Emo - AI Agent with Gmail Integration and Memory
Built with Streamlit, Google Gemini 2.5 Flash, Gmail API, and ChromaDB
"""

import os
import json
import time
import threading
from datetime import datetime

# HTBuilder for custom HTML elements (like demo-ai-assistant)
from htbuilder.units import rem
from htbuilder import div, styles

# Third-party imports
import streamlit as st
from dotenv import load_dotenv

# Chat History
from history import (
    load_all_sessions,
    save_session,
    create_new_session,
    generate_title,
    delete_session,
    get_session_messages,
    get_sessions_sorted
)

# Universal Context (4 Pillars)
from state import (
    initialize_context,
    format_system_prompt,
    load_todo_list,
    get_current_datetime
)

# Session-scoped memory management
from tools import set_current_session_id, clear_session_short_term_memory

# Config
from config import (
    GEMINI_MODEL, GEMINI_API_KEY, get_gemini_model,
    get_chroma_collection, query_memory, format_memories_for_context,
    _chroma_client, _chroma_collection, _chroma_lock, CHROMA_PATH as CONFIG_CHROMA_PATH
)

# NEW MODULAR IMPORTS
from utils import stream_data, render_message_with_latex, process_latex_content
from parsers import parse_attachment
from task_manager import TaskManager, get_task_manager, get_smart_reminders, add_todo, get_todos, complete_todo
from quiz import generate_quiz, render_quiz
from web_tools import read_web_page, watch_youtube, get_news_headlines
from gmail_tools import (
    authenticate_gmail, get_gmail_service, disconnect_gmail, reconnect_gmail,
    test_gmail_connection, quick_gmail_search, get_email_by_index,
    analyze_attachment, get_full_email, check_gmail_and_learn, fetch_email_attachments
)
from prompts import get_universal_context, build_dynamic_system_prompt, get_openai_tools
from chat_engine import (
    classify_query, select_model_for_task, prepare_tool_args,
    get_chat_messages, chat_with_emo, setup_tools
)


# Load environment variables
load_dotenv()

# ChromaDB setup (kept for memory functions in tools.py)
CHROMA_PATH = "./emo_memory"
TODO_FILE = 'todo.json'

# =============================================================================
# TASK 6: THE FRONTEND (Streamlit)
# =============================================================================

def get_custom_css():
    """Return minimal custom CSS for clean UI and vertical centering."""
    return """
    <style>
        /* Hide streamlit defaults */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Center the main content when in initial state */
        .stApp > header {
            background-color: transparent;
        }
        
        div.block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Custom classes for centering */
        .centered-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 60vh;
            text-align: center;
        }
        
        /* Section labels */
        .section-label {
            font-size: 0.7rem;
            font-weight: 500;
            color: #888;
            padding: 0.25rem 0;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
    </style>
    """


def initialize_session_state():
    """
    Initialize Streamlit session state variables.
    """
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'gmail_authenticated' not in st.session_state:
        st.session_state.gmail_authenticated = False
    
    # Initialize Universal Context
    if 'universal_context' not in st.session_state:
        st.session_state.universal_context = initialize_context()
    
    # Initialize Chat History session
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    
    # Set current session ID for short-term memory scoping
    if st.session_state.current_session_id:
        set_current_session_id(st.session_state.current_session_id)
    
    # AI Thinking mode - default ON
    if 'show_thinking' not in st.session_state:
        st.session_state.show_thinking = True
    
    # UI state
    if 'show_settings' not in st.session_state:
        st.session_state.show_settings = False
    
    if 'show_memory_browser' not in st.session_state:
        st.session_state.show_memory_browser = False
    
    if 'chat_search' not in st.session_state:
        st.session_state.chat_search = ""


def display_chat_history():
    """
    Display all messages in the chat history with LaTeX and enhanced markdown support.
    Also handles special content like interactive quizzes.
    """
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            content = message['content']
            
            # Check if this message contains a quiz
            if 'QUIZ_CREATED:' in content:
                # Extract quiz ID and render it
                import re
                quiz_match = re.search(r'QUIZ_CREATED:([^\|]+)\|([^\|]+)\|(.+)', content)
                if quiz_match:
                    quiz_id = quiz_match.group(1)
                    quiz_title = quiz_match.group(2)
                    quiz_info = quiz_match.group(3)
                    
                    # Show a nice message and render the quiz
                    st.success(f"🎓 Quiz ready: **{quiz_title}** ({quiz_info})")
                    render_quiz(quiz_id)
                else:
                    # Fallback to normal rendering
                    render_message_with_latex(content)
            else:
                # Use LaTeX-aware rendering
                render_message_with_latex(content)


@st.dialog("Settings", width="small")
def settings_dialog():
    """Settings dialog - compact."""
    context = get_universal_context()
    identity = context.get('identity', {})
    env = context.get('env', {})
    
    # User + Date inline
    user_name = identity.get('user_name', 'User')
    st.caption(f"👤 {user_name} · {env.get('current_date', '')}")
    
    # AI Toggle
    show_thinking = st.toggle(
        "Show AI reasoning",
        value=st.session_state.get('show_thinking', True),
        key="dialog_thinking"
    )
    st.session_state.show_thinking = show_thinking
    
    st.divider()
    
    # Status - inline compact
    st.caption("**Status**")
    
    # Build status line
    gemini_ok = "✅" if GEMINI_API_KEY else "❌"
    gmail_ok = "✅" if st.session_state.gmail_authenticated else "⚪"
    
    try:
        collection = get_chroma_collection()
        mem_count = collection.count() if collection else 0
    except:
        mem_count = 0
    
    st.caption(f"Gemini {gemini_ok} · Gmail {gmail_ok} · Memory: {mem_count}")
    
    # Gmail connect if needed
    if not st.session_state.gmail_authenticated:
        if st.button("Connect Gmail", key="gmail_connect", use_container_width=True):
            try:
                get_gmail_service()
                st.session_state.gmail_authenticated = True
                st.rerun()
            except Exception as e:
                st.error(str(e)[:30])
    else:
        # Gmail is connected - show management buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reconnect", key="gmail_reconnect", use_container_width=True):
                result = reconnect_gmail()
                if result is True:
                    st.success("Reconnected!")
                    st.rerun()
                else:
                    st.error(f"Failed: {result}")
        with col2:
            if st.button("❌ Disconnect", key="gmail_disconnect", use_container_width=True):
                if disconnect_gmail():
                    st.success("Disconnected")
                    st.rerun()
        
        # Test connection button
        if st.button("🧪 Test Connection", key="gmail_test", use_container_width=True):
            success, msg = test_gmail_connection()
            if success:
                st.success(msg)
            else:
                st.error(msg)
    
    st.divider()
    
    # Danger zone
    if st.button("🗑️ Clear All Memory", type="secondary", use_container_width=True):
        try:
            import shutil
            global _chroma_client, _chroma_collection
            
            # Reset the global ChromaDB client and collection first
            with _chroma_lock:
                _chroma_client = None
                _chroma_collection = None
            
            # Clear session state
            if 'chroma_collection' in st.session_state:
                del st.session_state.chroma_collection
            
            # Now delete the folder
            if os.path.exists(CHROMA_PATH):
                shutil.rmtree(CHROMA_PATH)
            
            st.success("✅ Memory cleared!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


@st.dialog("Memory", width="large")
def memory_dialog():
    """Memory browser - compact."""
    try:
        collection = get_chroma_collection()
        if collection and collection.count() > 0:
            all_docs = collection.get(include=['metadatas', 'documents'])
            
            if all_docs['ids']:
                st.caption(f"{len(all_docs['ids'])} memories stored")
                
                for i, doc_id in enumerate(all_docs['ids'][:10]):
                    meta = all_docs['metadatas'][i] if all_docs['metadatas'] else {}
                    doc_text = all_docs['documents'][i][:150] if all_docs['documents'] else ""
                    subject = meta.get('subject', meta.get('summary', doc_text[:50]))
                    doc_type = meta.get('type', 'doc')
                    
                    with st.expander(f"**{subject[:40]}...** `{doc_type}`" if len(subject) > 40 else f"**{subject}** `{doc_type}`"):
                        st.text(doc_text[:300] + "..." if len(doc_text) > 300 else doc_text)
                
                if len(all_docs['ids']) > 10:
                    st.caption(f"+{len(all_docs['ids']) - 10} more")
        else:
            st.caption("No memories yet")
    except:
        st.caption("Could not load")


@st.dialog("Tasks", width="large")
def tasks_dialog():
    """Task dialog - full width with complete content."""
    task_manager = get_task_manager()
    pending = task_manager.get_pending_tasks()
    done = [t for t in task_manager.get_all_tasks() if t['status'] == 'done']
    
    # Quick add
    new_task = st.text_input("", placeholder="Add new task...", key="dialog_new_task", label_visibility="collapsed")
    if new_task:
        task_manager.add_task(new_task)
        st.rerun()
    
    st.divider()
    
    # Pending tasks - full content
    if pending:
        st.markdown(f"**Pending ({len(pending)})**")
        for task in pending:
            c1, c2 = st.columns([10, 1])
            with c1:
                # Show full task content
                st.markdown(f"• {task['task']}")
            with c2:
                if st.button("✓", key=f"c_{task['id']}", help="Mark done"):
                    task_manager.complete_task_by_id(task['id'])
                    st.rerun()
    else:
        st.caption("No pending tasks")
    
    # Completed - collapsible with full content
    if done:
        st.divider()
        with st.expander(f"Completed ({len(done)})"):
            for t in done[-5:]:
                st.caption(f"- {t['task']}")
            if len(done) > 5:
                st.caption(f"... and {len(done) - 5} more")
            if st.button("Clear completed", key="clear_done", use_container_width=True):
                task_manager.delete_completed()
                st.rerun()


def main():
    """
    Main Streamlit application - Demo-like UI (Clean, No Sidebar).
    """
    # Page configuration
    st.set_page_config(
        page_title="Emo",
        page_icon="◯",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # Get context data
    context = get_universal_context()
    identity = context.get('identity', {})
    
    # =========================
    # TOP NAVIGATION BAR
    # =========================
    top_col1, top_col2 = st.columns([6, 1])
    
    with top_col2:
        # Hamburger Menu
        with st.popover("Menu", use_container_width=True):
            st.markdown("**Tools**")
            if st.button("📝 Tasks", use_container_width=True):
                tasks_dialog()
            if st.button("🧠 Memo", use_container_width=True):
                memory_dialog()
            if st.button("⚙️ Settings", use_container_width=True):
                settings_dialog()
            
            st.divider()
            
            st.markdown("**Recent Chats**")
            sessions = get_sessions_sorted()
            if sessions:
                for session_id, session_data in sessions[:5]:
                    title = session_data.get("title", "New Chat")
                    is_current = session_id == st.session_state.current_session_id
                    display_title = title[:20] + "..." if len(title) > 20 else title
                    
                    if st.button(f"{'● ' if is_current else ''}{display_title}", key=f"nav_{session_id}", use_container_width=True):
                        st.session_state.current_session_id = session_id
                        st.session_state.messages = session_data.get("messages", [])
                        set_current_session_id(session_id)
                        if 'chat_session' in st.session_state:
                            del st.session_state.chat_session
                        st.rerun()
            else:
                st.caption("No recent chats")
                
            st.divider()
            
            # New Chat inside menu
            if st.button("＋ New Chat", key="menu_new_chat", use_container_width=True):
                new_id = create_new_session()
                st.session_state.current_session_id = new_id
                st.session_state.messages = []
                set_current_session_id(new_id)
                if 'chat_session' in st.session_state:
                    del st.session_state.chat_session
                st.rerun()

    # =========================
    # MAIN CONTENT
    # =========================
    
    has_history = len(st.session_state.messages) > 0
    
    if not has_history:
        # ---------------------------------------------------------------------
        # INITIAL STATE: Vertically Centered
        # ---------------------------------------------------------------------
        
        st.markdown('<div class="centered-container">', unsafe_allow_html=True)
        
        st.html(div(style=styles(font_size=rem(5), line_height=1))["◯"])
        st.title("Emo")
        # st.caption("Your AI Assistant with Memory & Tools")
        
        st.markdown('</div>', unsafe_allow_html=True)

        if prompt := st.chat_input("Message Emo..."):
            # Create session if none exists
            if not st.session_state.current_session_id:
                new_id = create_new_session()
                st.session_state.current_session_id = new_id
                set_current_session_id(new_id)
            
            st.session_state.messages.append({'role': 'user', 'content': prompt})
            generate_title(st.session_state.current_session_id, prompt)
            st.rerun()

    else:
        # ---------------------------------------------------------------------
        # CHAT STATE: Standard Layout
        # ---------------------------------------------------------------------
        
        # Title Row (Smaller - "Restart" style button as requested)
        c1, c2 = st.columns([8, 2])
        with c1:
             st.html(div(style=styles(font_size=rem(2), line_height=1))["◯"])
        with c2:
             if st.button("New Chat", key="top_new_chat", use_container_width=True):
                new_id = create_new_session()
                st.session_state.current_session_id = new_id
                st.session_state.messages = []
                set_current_session_id(new_id)
                if 'chat_session' in st.session_state:
                    del st.session_state.chat_session
                st.rerun()

        # Display history
        display_chat_history()
        
        # Chat Input
        if prompt := st.chat_input("Message Emo..."):
            
             # Add user message
            st.session_state.messages.append({
                'role': 'user',
                'content': prompt
            })
            
            # Display user message
            with st.chat_message('user'):
                render_message_with_latex(prompt)
            
            # Generate response
            with st.chat_message('assistant'):
                # Query memory (silent)
                memories = query_memory(prompt)
                memory_context = format_memories_for_context(memories)
                
                # Tool display container
                tool_container = st.container()
                
                # Get response
                show_thinking = st.session_state.get('show_thinking', True)
                result = chat_with_emo(prompt, memory_context, show_thinking, tool_container)
                
                # Display AI thinking
                thinking_text = result.get('thinking', '')
                if thinking_text and show_thinking:
                    with st.expander("💭 **Thinking**", expanded=False):
                        st.markdown(f"""
    <div style="font-size: 0.9rem; color: #8b949e; line-height: 1.6; padding: 0.5rem; background: rgba(139, 148, 158, 0.1); border-radius: 6px; border-left: 3px solid #58a6ff;">
    {thinking_text}
    </div>
    """, unsafe_allow_html=True)
                
                # Display response
                response_text = result.get('response', '')
                if response_text:
                    if 'QUIZ_CREATED:' in response_text:
                        import re
                        quiz_match = re.search(r'QUIZ_CREATED:([^\|]+)\|([^\|]+)\|(.+)', response_text)
                        if quiz_match:
                            quiz_id = quiz_match.group(1)
                            quiz_title = quiz_match.group(2)
                            quiz_info = quiz_match.group(3)
                            
                            st.success(f"🎓 Quiz ready: **{quiz_title}** ({quiz_info})")
                            render_quiz(quiz_id)
                        else:
                            render_message_with_latex(response_text)
                    else:
                        response_placeholder = st.empty()
                        full_response = ""
                        for word in stream_data(response_text):
                            full_response += word
                            response_placeholder.markdown(full_response + "▌")
                        response_placeholder.empty()
                        render_message_with_latex(full_response)
                response = response_text
            
            # Save to history
            st.session_state.messages.append({
                'role': 'assistant',
                'content': response
            })
            
            if st.session_state.current_session_id:
                save_session(st.session_state.current_session_id, st.session_state.messages)
            
            if st.session_state.get('todo_changed', False):
                st.session_state.todo_changed = False
                st.rerun()


if __name__ == "__main__":
    main()
