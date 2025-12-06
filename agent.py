"""
Emo2 - LangGraph Agent Entry Point
==================================
Main orchestration file that assembles the agent graph

This module:
1. Initializes the LangGraph StateGraph with EmoState
2. Configures nodes: context_loader, chatbot, tools
3. Implements conditional routing based on tool calls
4. Provides CLI interface for testing

Author: Senior AI Architect
Version: 2.0
"""

import os
from typing import Literal

from dotenv import load_dotenv

# LangChain / LangGraph imports
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition

# Local imports
from state import (
    EmoState,
    initialize_context,
    refresh_environment,
    format_system_prompt,
    build_full_system_prompt,
    update_working_memory,
)
from tools import ALL_TOOLS, read_web_page, watch_youtube, search_memory, recall_memory

# Load environment variables
load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

# Model configuration - optimized for 7B models
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 2048

# Base system instruction (static part)
BASE_SYSTEM_INSTRUCTION = """You are Emo2, an intelligent AI assistant with advanced capabilities.

## Your Core Abilities:
1. **Web Reading**: Use `read_web_page` to fetch and analyze web content
2. **YouTube Analysis**: Use `watch_youtube` to get video transcripts
3. **Memory Search**: Use `search_memory` to find saved information
4. **Memory Recall**: Use `recall_memory` to get full content by ID

## Guidelines:
- When given a URL, use the appropriate tool (web or YouTube)
- Always reference the UNIVERSAL CONTEXT for user preferences and current time
- Be concise but thorough in your responses
- If working memory has content, prioritize answering questions about it
- Proactively suggest adding tasks to the to-do list when appropriate

## Response Style:
- Match the user's communication style preference
- Use markdown formatting for clarity
- Include relevant timestamps from YouTube transcripts
- Cite sources when referencing web content"""


# =============================================================================
# NODE 1: CONTEXT LOADER
# =============================================================================

def load_context_node(state: EmoState) -> dict:
    """
    Node that refreshes environment context at the start of each invocation.
    
    This ensures the agent always has:
    - Current date and time
    - Fresh location data (if available)
    
    Args:
        state: Current EmoState
        
    Returns:
        State update with refreshed environment context
    """
    return refresh_environment(state)


# =============================================================================
# NODE 2: CHATBOT (Core Reasoning)
# =============================================================================

def create_chatbot_node(model: ChatGoogleGenerativeAI):
    """
    Factory function to create the chatbot node with bound tools.
    
    Args:
        model: The LLM instance with tools bound
        
    Returns:
        Chatbot node function
    """
    
    def chatbot_node(state: EmoState) -> dict:
        """
        The main reasoning node that processes user input.
        
        Critical Implementation Details:
        1. Injects Universal Context as system message
        2. Formats context BEFORE each LLM call (not just at start)
        3. Handles tool calls automatically via LangGraph
        
        Args:
            state: Current EmoState with messages and context
            
        Returns:
            State update with new AI message
        """
        # === CRITICAL: Format Universal Context ===
        # This is injected fresh on each call to ensure time accuracy
        context_block = format_system_prompt(state)
        full_system_prompt = f"{BASE_SYSTEM_INSTRUCTION}\n\n{context_block}"
        
        # Build message list with system prompt
        messages = [SystemMessage(content=full_system_prompt)]
        
        # Add conversation history
        for msg in state.get("messages", []):
            messages.append(msg)
        
        # Invoke the model
        response = model.invoke(messages)
        
        # Return state update (LangGraph handles message appending)
        return {"messages": [response]}
    
    return chatbot_node


# =============================================================================
# NODE 3: TOOLS (Execution)
# =============================================================================

def create_tool_node():
    """
    Create the tool execution node.
    
    Uses LangGraph's ToolNode for automatic tool dispatch.
    """
    return ToolNode(ALL_TOOLS)


# =============================================================================
# WORKING MEMORY UPDATER
# =============================================================================

def update_memory_from_tools(state: EmoState) -> dict:
    """
    Post-tool node that updates working memory with tool results.
    
    Extracts content from tool responses and stores in working memory
    for easy reference in subsequent turns.
    
    Args:
        state: Current state after tool execution
        
    Returns:
        State update with working memory (if applicable)
    """
    messages = state.get("messages", [])
    
    if not messages:
        return {}
    
    # Look at the last message (should be tool result)
    last_message = messages[-1]
    
    # Check if it's a tool message with content
    if hasattr(last_message, 'content') and last_message.content:
        content = last_message.content
        
        # Detect if this is web or YouTube content
        if "=== WEB CONTENT" in content or "=== YOUTUBE TRANSCRIPT" in content:
            # Extract source URL if present
            source_url = None
            if "Source:" in content:
                import re
                match = re.search(r'Source:\s*(\S+)', content)
                if match:
                    source_url = match.group(1)
            
            # Update working memory
            return update_working_memory(state, content, source_url)
    
    return {}


# =============================================================================
# GRAPH ASSEMBLY
# =============================================================================

def build_agent_graph() -> StateGraph:
    """
    Assemble the complete agent graph.
    
    Graph Structure:
    ```
    START
      │
      ▼
    ┌─────────────────┐
    │ load_context    │  ← Refresh time/environment
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │    chatbot      │  ← Main reasoning with Universal Context
    └────────┬────────┘
             │
             ▼
        [tools_condition]
           /        \
          /          \
         ▼            ▼
    ┌─────────┐    ┌─────┐
    │  tools  │    │ END │
    └────┬────┘    └─────┘
         │
         │ (loop back)
         ▼
    ┌─────────────────┐
    │    chatbot      │
    └─────────────────┘
    ```
    
    Returns:
        Compiled LangGraph application
    """
    # Initialize the LLM with tools
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    
    # Bind tools to the model
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    
    # Create nodes
    chatbot_node = create_chatbot_node(llm_with_tools)
    tool_node = create_tool_node()
    
    # Initialize the graph
    graph = StateGraph(EmoState)
    
    # Add nodes
    graph.add_node("load_context", load_context_node)
    graph.add_node("chatbot", chatbot_node)
    graph.add_node("tools", tool_node)
    
    # Set entry point
    graph.set_entry_point("load_context")
    
    # Add edges
    graph.add_edge("load_context", "chatbot")
    
    # Conditional edge: chatbot -> tools OR end
    graph.add_conditional_edges(
        "chatbot",
        tools_condition,  # Built-in condition that checks for tool calls
        {
            "tools": "tools",
            END: END,
        }
    )
    
    # Loop: tools -> chatbot (to process tool results)
    graph.add_edge("tools", "chatbot")
    
    # Compile the graph
    return graph.compile()


# =============================================================================
# MAIN APPLICATION
# =============================================================================

# Global compiled graph
app = build_agent_graph()


def run_agent(user_input: str, state: EmoState = None) -> tuple[str, EmoState]:
    """
    Run the agent with user input.
    
    Args:
        user_input: The user's message
        state: Optional existing state (creates new if None)
        
    Returns:
        Tuple of (response_text, updated_state)
    """
    # Initialize state if not provided
    if state is None:
        state = initialize_context()
    
    # Add user message to state
    state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]
    
    # Run the graph
    result = app.invoke(state)
    
    # Extract the last AI message
    messages = result.get("messages", [])
    response_text = ""
    
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            response_text = msg.content
            break
    
    return response_text, result


def run_conversation():
    """
    Run an interactive conversation loop.
    """
    print("\n" + "=" * 64)
    print("        Emo2 - LangGraph Agent")
    print("        Type 'quit' to exit, 'clear' to reset")
    print("=" * 64 + "\n")
    
    # Initialize state
    state = initialize_context()
    
    while True:
        try:
            # Get user input
            user_input = input("\n🧑 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'clear':
                state = initialize_context()
                print("🔄 Conversation cleared!")
                continue
            
            # Run agent
            print("\n🤖 Emo2: ", end="", flush=True)
            response, state = run_agent(user_input, state)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    """
    CLI test for the agent.
    
    Test scenarios:
    1. YouTube transcript: "Tóm tắt video youtube này: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    2. Web reading: "Đọc trang web này: https://www.python.org"
    3. Memory search: "Tìm trong bộ nhớ về budget"
    """
    import sys
    
    # Check for command line argument
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        print(f"\n📝 Query: {query}")
        print("-" * 64)
        
        response, _ = run_agent(query)
        print(f"\n🤖 Emo2:\n{response}")
    else:
        # Interactive mode
        print("\n🎬 Running test query...")
        print("-" * 64)
        
        # Test with YouTube
        test_query = "Tóm tắt video youtube này: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        print(f"📝 Test Query: {test_query}\n")
        
        response, _ = run_agent(test_query)
        print(f"🤖 Emo2:\n{response}")
        
        print("\n" + "=" * 64)
        print("Starting interactive mode...")
        print("=" * 64)
        
        # Start conversation loop
        run_conversation()
