# Copyright 2025 Snowflake Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from htbuilder.units import rem
from htbuilder import div, styles
import datetime
import time
import streamlit as st

# EMO IMPORTS
from chat_engine import chat_with_emo
from state import initialize_context, get_current_datetime
from history import save_session, create_new_session, generate_title
from tools import set_current_session_id
from config import format_memories_for_context, query_memory
from task_manager import get_smart_reminders

st.set_page_config(page_title="Emo AI Assistant", page_icon="◯")

# -----------------------------------------------------------------------------
# Set things up.

def initialize_session_state():
    """Initialize Streamlit session state variables for Emo."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
        new_id = create_new_session()
        st.session_state.current_session_id = new_id
        set_current_session_id(new_id)
    
    # Initialize Universal Context if needed (legacy Emo requirement)
    if 'universal_context' not in st.session_state:
        st.session_state.universal_context = initialize_context()

    # Sync Emo backend memory with UI memory
    # chat_with_emo uses 'chat_messages' key
    st.session_state.chat_messages = st.session_state.messages

initialize_session_state()

DEBUG_MODE = st.query_params.get("debug", "false").lower() == "true"

SUGGESTIONS = {
    ":blue[:material/checklist:] What are my tasks?": (
        "What are my pending tasks and todos?"
    ),
    ":green[:material/mail:] Summarize my last email": (
        "Check my last email and summarize it for me."
    ),
    ":orange[:material/psychology:] Create a quiz": (
        "Create a quiz about Python programming."
    ),
    ":violet[:material/newspaper:] Tech News": (
        "What are the latest tech news headlines?"
    ),
}

# -----------------------------------------------------------------------------
# Helpers

def response_generator(text):
    """Yields words from the text to simulate streaming."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)

def send_telemetry(**kwargs):
    """Records some telemetry about questions being asked."""
    # Placeholder for Emo telemetry
    pass

def show_feedback_controls(message_index):
    """Shows the "How did I do?" control."""
    # kept simple or removed based on preference. Keeping simple for now.
    pass 

@st.dialog("Legal disclaimer")
def show_disclaimer_dialog():
    st.caption("""
            This AI assistant (Emo) is an experimental project. 
            Answers may be inaccurate. Do not use for critical advice.
            Emo uses your Gemini API key and accesses your defined tools (Gmail, etc).
        """)

# -----------------------------------------------------------------------------
# Draw the UI.

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.markdown(
        '<h1 style="font-size: 2rem; font-weight: 600; margin: 0; text-align: center;">Golden hour thinking, Josh.</h1>',
        unsafe_allow_html=True,
    )

user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)

user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)

user_first_interaction = (
    user_just_asked_initial_question or user_just_clicked_suggestion
)

has_message_history = (
    "messages" in st.session_state and len(st.session_state.messages) > 0
)

# Show a different UI when the user hasn't asked a question yet.
if not user_first_interaction and not has_message_history:
    st.session_state.messages = []

    with st.container():
        st.chat_input("Emoing...", key="initial_question")

        selected_suggestion = st.pills(
            label="Examples",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )

    st.button(
        "&nbsp;:small[:gray[:material/balance: Legal disclaimer]]",
        type="tertiary",
        on_click=show_disclaimer_dialog,
    )

    st.stop()

# Show chat input at the bottom when a question has been asked.
user_message = st.chat_input("Ask a follow-up...")

if not user_message:
    if user_just_asked_initial_question:
        user_message = st.session_state.initial_question
    if user_just_clicked_suggestion:
        user_message = SUGGESTIONS[st.session_state.selected_suggestion]

with title_row:
    def clear_conversation():
        # Create new session in backend
        new_id = create_new_session()
        st.session_state.current_session_id = new_id
        set_current_session_id(new_id)
        
        # Clear UI state
        st.session_state.messages = []
        st.session_state.initial_question = None
        st.session_state.selected_suggestion = None

    st.button(
        "Restart",
        icon=":material/refresh:",
        on_click=clear_conversation,
    )

if "prev_question_timestamp" not in st.session_state:
    st.session_state.prev_question_timestamp = datetime.datetime.fromtimestamp(0)

# Display chat messages from history as speech bubbles.
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.container()  # Fix ghost message bug.
        
        # Handle special quiz rendering if present in content
        if 'QUIZ_CREATED:' in message["content"]:
             st.info("Interactive Quiz (Update UI to support interactivity)")
             st.markdown(message["content"])
        else:
             st.markdown(message["content"])

if user_message:
    # When the user posts a message...
    
    # Clean latex $
    user_message = user_message.replace("$", r"\$")

    # Display message as a speech bubble.
    with st.chat_message("user"):
        st.text(user_message)

    # Display assistant response as a speech bubble.
    with st.chat_message("assistant"):
        
        # Add tool container for visible tool execution updates
        tool_container = st.container()

        with st.spinner("Thinking..."):
            # Prepare context
            memories = query_memory(user_message)
            memory_context = format_memories_for_context(memories)
            
            # CALL EMO BACKEND
            # We pass False for show_thinking first to get the raw result, 
            # but we can also display valid thinking steps if we want.
            # NOTE: chat_with_emo will append to st.session_state.messages since we aliased it!
            result = chat_with_emo(
                user_message, 
                memory_context, 
                show_thinking=True, 
                tool_display_container=tool_container
            )
            
            response_text = result.get('response', 'Sorry, I had trouble thinking.')
            thinking_text = result.get('thinking', '')

        # Put everything after the spinners in a container to fix the
        # ghost message bug.
        with st.container():
            # Show thinking if available
            if thinking_text:
                with st.expander("💭 Thinking process", expanded=False):
                    st.markdown(thinking_text)

            # Stream the LLM response.
            response = st.write_stream(response_generator(response_text))

            # Note: We do NOT append to st.session_state.messages here manually
            # because chat_with_emo already did it via the aliased list.

            # Save to backend history
            if st.session_state.current_session_id:
                save_session(st.session_state.current_session_id, st.session_state.messages)
                generate_title(st.session_state.current_session_id, user_message)

            # Other stuff.
            send_telemetry(question=user_message, response=response)
