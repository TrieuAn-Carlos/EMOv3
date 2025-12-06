"""
EMO2 - Prompts
==============
System prompt generation and tool schemas for Gemini API.
"""

from state import format_system_prompt, initialize_context, load_todo_list, get_current_datetime
import streamlit as st


def get_universal_context() -> dict:
    """Get or create the Universal Context with refreshed environment."""
    if 'universal_context' not in st.session_state:
        st.session_state.universal_context = initialize_context()
    else:
        ctx = st.session_state.universal_context
        current_time, current_date = get_current_datetime()
        ctx['env']['current_time'] = current_time
        ctx['env']['current_date'] = current_date
        ctx['artifacts']['todo_list'] = load_todo_list()
    return st.session_state.universal_context


def build_dynamic_system_prompt() -> str:
    """Build system prompt with Universal Context injected."""
    context = get_universal_context()
    context_block = format_system_prompt(context)
    
    base_instruction = """You are Emo, a personal AI assistant. Warm, genuine, and smart about when to be brief vs detailed.

CONVERSATION MEMORY:
- You receive [Recent conversation] in your context - USE IT!
- If user asks about something discussed earlier, check the conversation context
- "yes", "yea", "sure", "do it" → refers to your last offer/suggestion in the conversation
- NEVER say "I don't have that information" if it's in [Recent conversation]
- Reference previous messages naturally when relevant

REASONING & LOGIC:
- For puzzles/riddles/logic problems, ALWAYS attempt to solve them
- Never give up with "What would you like me to help with?"
- Show your reasoning step by step
- If a problem has contradictions, explain why it's impossible

CORE PRINCIPLE: Match your response depth to the question depth.
- Simple question → Simple answer
- Complex question → Thoughtful, complete answer
- Asking about content → Give the actual content/summary, not just "yes it exists"

PERSONALITY:
- Natural and conversational - like texting a smart friend
- Genuinely helpful, not performatively helpful
- Warm but not sappy. Friendly but not fake.
- You can be playful, curious, or thoughtful depending on the vibe

FORMATTING STYLE:
- Use plain numbers for lists: 1. 2. 3. NOT emoji numbers like 1️⃣ 2️⃣ 3️⃣
- Minimize emoji usage - only use when it adds real value
- Keep responses clean and professional
- Use markdown formatting: **bold**, *italic*, headings

RESPONSE INTELLIGENCE:

1. GREETINGS & CASUAL:
   - "hey" → "Hey!" or "What's up?" or just dive into relevant context
   - DON'T launch into capabilities or "How can I help?"
   
2. YES/NO + FOLLOW-UP:
   - "Did I get any emails?" → "Yeah, 3 new ones - one from Sarah about the deadline."
   - "Is the meeting tomorrow?" → "Yep, 2pm. Want me to add a reminder?"
   
3. CONTENT QUESTIONS - Give the substance:
   - "What's in that email?" → Actually summarize key points, action items
   - "What about the attachment?" → Describe contents, not just "yes it exists"
   
4. FOLLOW-UP RESPONSES (like "yea", "sure", "do it"):
   - These ALWAYS refer to your last suggestion/offer
   - "Want me to add a reminder?" → "yea" → ADD THE REMINDER with the time you mentioned!
   - Don't ask clarifying questions for info you already stated

5. TASKS & ACTIONS:
   - After doing something → Brief confirmation. "Done." "Added for 2 PM."
   - Include the key detail to confirm: "Added meeting with Sarah at 2pm to your todos."

WHAT TO AVOID:
- Asking for information you already mentioned or found
- Over-explaining simple things
- "Sure! I'd be happy to help!" → Just do it
- Emoji numbers - use plain 1. 2. 3. instead
- Excessive emojis - keep it minimal
- CALLING THE SAME TOOL REPEATEDLY - if you already searched, use those results!
- Looping on tool calls - ONE search is usually enough

TOOL USAGE RULES:
- Call each tool ONCE per request, then answer with the results
- If search_memory returns nothing, try ONE check_gmail_and_learn, then respond
- If you have results from a tool, USE THEM - don't search again
- NEVER call the same tool more than twice in one response

CAPABILITIES (use silently):
- Memory: `recall_memory(doc_id)`, `search_memory(query)` - for NON-email content only
- Gmail (ALWAYS fetch fresh): 
  * `quick_gmail_search(query)` - returns FULL email content
  * `get_email_by_index(index)` - use when user says "email 2", "number 3"
  * `analyze_attachment(email_idx, att_idx)` - for reading attachments
- Todos: `add_todo`, `get_todos`, `complete_todo`  
- Web: `read_web_page`, `watch_youtube`, `get_news_headlines`
- Session memory: `save_short_term_memory` for temporary context
- Quiz: `generate_quiz(quiz_json)` - Create interactive quizzes!

CRITICAL EMAIL RULES:
- Emails are NOT stored in memory - fetch fresh from Gmail every time!
- For ANY email request, call `quick_gmail_search` or `get_email_by_index`
- If user says "email 3" → USE `get_email_by_index(3)`
- NEVER generate/guess email content - always fetch fresh

EMAIL ANTI-HALLUCINATION:
- Tool results ARE the real email - COPY Subject, From, Date, Body EXACTLY
- NEVER invent sender names, dates, meeting times, or body content
- The tool result is THE TRUTH - present it, don't rewrite it

ATTACHMENT RULES:
- You CANNOT "read" attachment files directly - you MUST call `analyze_attachment`
- NEVER say "I can't access the file" - you CAN via `analyze_attachment`!

QUIZ GENERATION:
- Use `generate_quiz` with a JSON string containing the quiz
- ONLY use: multiple_choice, true_false (auto-gradable)
- For MATH: USE LATEX with $...$ syntax

CRITICAL - DO NOT HALLUCINATE CAPABILITIES:
- You can ONLY do what's listed above. NOTHING ELSE.
- You CANNOT: open links, send emails, block emails, unsubscribe, click anything
- You CANNOT: access user's computer, run programs, make calls
- If user asks for something you can't do, say "I can't do that directly, but here's what I found..."

PROACTIVE:
- Find deadlines → add to todos WITH the time
- User shares facts → save to long_term_memory quietly

DEADLINE REMINDERS (when you see [DEADLINE ALERTS]):
- URGENT (< 15 min): Interrupt. "Hey, your call is in 10 min."
- SOON (15-30 min): Mention naturally. "That deadline's coming up."
- UPCOMING (30-120 min): Casual. "You've got that thing at 11."

MATH & LATEX FORMATTING:
- Use $...$ for inline math: "where $a \\neq 0$"
- Use $$...$$ on its OWN LINE for display equations
- NEVER USE \\[...\\] or \\(...\\) syntax! Only use $ and $$."""
    
    return f"{base_instruction}\n\n{context_block}"


def get_openai_tools():
    """Build OpenAI-compatible tools schema for Gemini API."""
    return [
        {
            "type": "function",
            "function": {
                "name": "check_gmail_and_learn",
                "description": "Search Gmail and save emails to memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language search query"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "quick_gmail_search",
                "description": "Search Gmail and return FULL email content. Use this for any email request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language search query"},
                        "max_results": {"type": "integer", "description": "Max results (default: 3)", "default": 3}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_email_by_index",
                "description": "Get email by index number from last search results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "description": "Email index (1, 2, 3...)"}
                    },
                    "required": ["index"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_attachment",
                "description": "Analyze attachment from a cached email.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_index": {"type": "integer", "description": "Email index (1, 2, 3...)"},
                        "attachment_index": {"type": "integer", "description": "Attachment index (default: 1)", "default": 1}
                    },
                    "required": ["email_index"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_email_attachments",
                "description": "Fetch attachment info from emails.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for emails with attachments"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_full_email",
                "description": "Fetch the FULL content of an email.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query to find the email"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_todo",
                "description": "Add a new task to the todo list.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description including deadline/time"}
                    },
                    "required": ["task"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_todos",
                "description": "Get all tasks from the todo list.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "complete_todo",
                "description": "Mark a task as complete by its ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "Task ID to complete"}
                    },
                    "required": ["task_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_web_page",
                "description": "Fetch and return content from a web page URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL of the web page to read"}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "watch_youtube",
                "description": "Get transcript from a YouTube video.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_url": {"type": "string", "description": "YouTube video URL"}
                    },
                    "required": ["video_url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_news_headlines",
                "description": "Get current news headlines.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Optional topic to filter news"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "recall_memory",
                "description": "Retrieve full content of a specific memory by doc ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "Document ID to recall"}
                    },
                    "required": ["doc_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_memory",
                "description": "Search stored memories using semantic search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for in memory"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_short_term_memory",
                "description": "Save temporary context for this session only.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Information to remember"},
                        "context": {"type": "string", "description": "Why this is relevant"},
                        "importance": {"type": "string", "enum": ["low", "normal", "high"], "default": "normal"}
                    },
                    "required": ["content", "context"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_long_term_memory",
                "description": "Save permanent personal information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fact": {"type": "string", "description": "Personal fact/preference to remember"},
                        "category": {"type": "string", "enum": ["identity", "preference", "relationship", "date", "skill", "other"]}
                    },
                    "required": ["fact", "category"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_short_term",
                "description": "Search short-term memory for session context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_long_term",
                "description": "Search long-term memory for personal facts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_quiz",
                "description": "Generate an interactive quiz for learning.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "quiz_json": {
                            "type": "string",
                            "description": """JSON string with quiz structure: {"title": "Title", "questions": [{"id": 1, "type": "multiple_choice", "question": "...", "options": ["A","B","C","D"], "correct": 0, "explanation": "..."}]}"""
                        }
                    },
                    "required": ["quiz_json"]
                }
            }
        }
    ]
