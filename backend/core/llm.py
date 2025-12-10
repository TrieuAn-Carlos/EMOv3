"""
Core LLM Module
===============
Centralized factory for LLM clients.
Supports Gemini (Google) and Friendli.ai (Emo model).
"""

import os
from typing import Optional, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from core.config import (
    GEMINI_API_KEY,
    GEMMA_27B_MODEL,
    FRIENDLI_TOKEN,
    FRIENDLI_API_BASE,
    FRIENDLI_MODEL,
    LLM_PROVIDER,
    TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    REQUEST_TIMEOUT
)


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    streaming: bool = False
) -> Any:
    """
    Get an LLM client instance based on configuration.
    
    Args:
        provider: Override configured provider ("gemini" or "litgpt")
        model: Override configured model name
        temperature: Override configured temperature
        max_tokens: Override configured max tokens
        streaming: Enable streaming
        
    Returns:
        LangChain Chat Model instance
    """
    provider = provider or LLM_PROVIDER
    temp = temperature if temperature is not None else TEMPERATURE
    tokens = max_tokens if max_tokens is not None else MAX_OUTPUT_TOKENS
    
    if provider == "friendli":
        if not FRIENDLI_TOKEN:
            raise ValueError("FRIENDLI_TOKEN not set in environment variables")
            
        print(f"🔌 Initializing Friendli.ai Connection (Emo)")
        return ChatOpenAI(
            model=model or FRIENDLI_MODEL,
            openai_api_key=FRIENDLI_TOKEN,
            openai_api_base=FRIENDLI_API_BASE,
            temperature=temp,
            max_tokens=tokens,
            timeout=REQUEST_TIMEOUT,
            streaming=streaming,
        )
        
    elif provider == "gemini":
        if not GEMINI_API_KEY:
            # Fallback or error is handled by the caller or library usually, 
            # but let's be explicit if we can.
            pass
            
        return ChatGoogleGenerativeAI(
            model=model or GEMMA_27B_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=temp,
            max_output_tokens=tokens,
            streaming=streaming,
            convert_system_message_to_human=True, # Often needed for some Google models
        )
        
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_embedding_model():
    """Reserved for future embedding model centralization."""
    pass
