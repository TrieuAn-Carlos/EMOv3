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
    TEMPERATURE,
    GEMINI_API_KEY,
    GEMMA_27B_MODEL,
    FRIENDLI_TOKEN,
    FRIENDLI_API_BASE,
    FRIENDLI_MODEL,
    LLM_PROVIDER,
    MAX_OUTPUT_TOKENS,
    TITLE_MAX_TOKENS,
    REQUEST_TIMEOUT,
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
    "TEMPERATURE",
    "GEMINI_API_KEY",
    "GEMMA_27B_MODEL",
    "FRIENDLI_TOKEN",
    "FRIENDLI_API_BASE",
    "FRIENDLI_MODEL",
    "LLM_PROVIDER",
    "MAX_OUTPUT_TOKENS",
    "TITLE_MAX_TOKENS",
    "REQUEST_TIMEOUT",
    "BASE_DIR",
    "USER_CONFIG_FILE",
    "TODO_FILE",
    "CHROMA_PATH",
]
