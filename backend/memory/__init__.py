"""
EMO Backend - Memory Module
============================
ChromaDB-based vector memory system.
"""

from .chroma_memory import (
    get_chroma_collection,
    query_memory,
    add_memory,
    format_memories_for_context,
    get_memory_stats,
)

from .memory_tools import (
    search_memory,
    recall_memory,
    save_long_term_memory,
    query_long_term,
)

__all__ = [
    # Core functions
    "get_chroma_collection",
    "query_memory",
    "add_memory",
    "format_memories_for_context",
    "get_memory_stats",
    # Tools
    "search_memory",
    "recall_memory",
    "save_long_term_memory",
    "query_long_term",
]
