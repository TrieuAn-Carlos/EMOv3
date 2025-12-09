"""
Title Generator Service
Auto-generate chat session titles using configured LLM provider
"""

import os
from typing import Optional, List
from langchain_core.messages import HumanMessage
from core.llm import get_llm
from core.config import TITLE_MAX_TOKENS

class TitleGenerator:
    """Service to generate titles for chat sessions"""
    
    def __init__(self):
        # LLM initialized on demand to allow hot-reloading context if needed
        pass
    
    def generate_title(self, messages: List[dict], max_length: int = 30) -> str:
        """
        Generate title based on the first few messages of conversation
        
        Args:
            messages: List of message dicts with keys 'role' and 'content'
            max_length: Max length of title
            
        Returns:
            Generated title string, fallback to default if fails
        """
        if not messages:
            return "Cuộc trò chuyện mới"
        
        # Get first user message
        first_user_message = None
        for msg in messages:
            if msg.get("role") == "user" and msg.get("content"):
                first_user_message = msg["content"]
                break
        
        if not first_user_message:
            return "Cuộc trò chuyện mới"
        
        # Truncate if message too long
        if len(first_user_message) > 500:
            first_user_message = first_user_message[:500] + "..."
        
        try:
            llm = get_llm(max_tokens=TITLE_MAX_TOKENS)
            
            prompt = f"""Tạo một tiêu đề ngắn gọn (tối đa 5 từ) bằng tiếng Việt cho cuộc trò chuyện bắt đầu bằng tin nhắn này.
Chỉ trả về tiêu đề, không có dấu ngoặc kép, không có giải thích thêm.
Tiêu đề phải phù hợp cho học sinh, dễ hiểu và thân thiện.

Tin nhắn đầu tiên của người dùng: "{first_user_message}"

Tiêu đề:"""
            
            response = llm.invoke([HumanMessage(content=prompt)])
            ai_title = response.content.strip().strip('"\'')
            
            # Validate and use AI title
            if ai_title and len(ai_title) <= 100:
                # Truncate if needed
                if len(ai_title) > max_length:
                    ai_title = ai_title[:max_length].rsplit(' ', 1)[0] + "..."
                return ai_title
            else:
                return self._fallback_title(first_user_message, max_length)
                
        except Exception as e:
            print(f"⚠️ Title generation error: {e}")
            return self._fallback_title(first_user_message, max_length)
    
    def _fallback_title(self, message: str, max_length: int) -> str:
        """
        Fallback title generation when API fails
        Just take the beginning of the message
        
        Args:
            message: User message
            max_length: Max title length
            
        Returns:
            Truncated message as title
        """
        # Remove newlines and extra spaces
        clean_message = " ".join(message.split())
        
        # Truncate
        if len(clean_message) <= max_length:
            return clean_message
        
        # Cut at word boundary
        truncated = clean_message[:max_length].rsplit(' ', 1)[0]
        return truncated + "..."
    
    def generate_title_from_session(self, session_messages: list) -> str:
        """
        Wrapper method for generate_title from session messages
        
        Args:
            session_messages: List of Message objects from database
            
        Returns:
            Generated title
        """
        # Convert Message objects to dicts
        messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in session_messages
        ]
        
        return self.generate_title(messages)


# Singleton instance
_title_generator = None

def get_title_generator() -> TitleGenerator:
    """Get singleton instance of TitleGenerator"""
    global _title_generator
    if _title_generator is None:
        _title_generator = TitleGenerator()
    return _title_generator
