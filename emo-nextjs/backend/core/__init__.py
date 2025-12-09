"""
EMO Backend Core Module
=======================
Central state, config, and context management.
"""

from .state import (
    IdentityContext,
    EnvironmentContext,
    WorkingMemory,
    Artifacts,
    EmoState,
    initialize_context,
    format_context_block,
    get_current_datetime,
)

from .config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    TEMPERATURE,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMMA_27B_MODEL,
    USE_GEMMA,
    MAX_OUTPUT_TOKENS,
    TITLE_MAX_TOKENS,
    REQUEST_TIMEOUT,
    TEMPERATURE,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMMA_27B_MODEL,
    BASE_DIR,
    USER_CONFIG_FILE,
    TODO_FILE,
    CHROMA_PATH,
)


__all__ = [
    # State
    "IdentityContext",
    "EnvironmentContext",
    "WorkingMemory",
    "Artifacts",
    "EmoState",
    "initialize_context",
    "format_context_block",
    "get_current_datetime",
    # Config
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "TEMPERATURE",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMMA_27B_MODEL",
    "BASE_DIR",
    "USER_CONFIG_FILE",
    "TODO_FILE",
    "CHROMA_PATH",
]
