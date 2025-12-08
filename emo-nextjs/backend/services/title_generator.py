"""
Title Generator Service
Auto-generate chat session titles using Groq API
"""

import os
from typing import Optional, List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "<GROQ_API_KEY>")
GROQ_MODEL = "llama-3.1-70b-versatile"  # Most capable model available


class TitleGenerator:
    """Service để generate title cho chat sessions"""
    
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model_name = GROQ_MODEL
    
    def generate_title(self, messages: List[dict], max_length: int = 30) -> str:
        """
        Generate title dựa trên messages đầu tiên của conversation
        
        Args:
            messages: List of message dicts với keys 'role' và 'content'
            max_length: Max length của title
            
        Returns:
            Generated title string, fallback về default nếu fail
        """
        if not messages:
            return "Cuộc trò chuyện mới"
        
        # Lấy message đầu tiên của user
        first_user_message = None
        for msg in messages:
            if msg.get("role") == "user" and msg.get("content"):
                first_user_message = msg["content"]
                break
        
        if not first_user_message:
            return "Cuộc trò chuyện mới"
        
        # Truncate nếu message quá dài
        if len(first_user_message) > 500:
            first_user_message = first_user_message[:500] + "..."
        
        # Try generate với Groq
        if not self.api_key:
            return self._fallback_title(first_user_message, max_length)
        
        try:
            llm = ChatGroq(
                model=self.model_name,
                api_key=self.api_key,
                temperature=0.7,
            )
            
            prompt = f"""Tạo một tiêu đề ngắn gọn (tối đa 5 từ) bằng tiếng Việt cho cuộc trò chuyện bắt đầu bằng tin nhắn này.
Chỉ trả về tiêu đề, không có dấu ngoặc kép, không có giải thích thêm.
Tiêu đề phải phù hợp cho học sinh, dễ hiểu và thân thiện.

Tin nhắn đầu tiên của người dùng: "{first_user_message}"

Tiêu đề:"""
            
            response = llm.invoke([HumanMessage(content=prompt)])
            ai_title = response.content.strip().strip('"\'')
            
            # Validate và sử dụng AI title
            if ai_title and len(ai_title) <= 100:
                # Truncate nếu cần
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
        Fallback title generation khi API fail
        Chỉ lấy đoạn đầu của message
        
        Args:
            message: User message
            max_length: Max title length
            
        Returns:
            Truncated message as title
        """
        # Remove newlines và extra spaces
        clean_message = " ".join(message.split())
        
        # Truncate
        if len(clean_message) <= max_length:
            return clean_message
        
        # Cut at word boundary
        truncated = clean_message[:max_length].rsplit(' ', 1)[0]
        return truncated + "..."
    
    def generate_title_from_session(self, session_messages: list) -> str:
        """
        Wrapper method cho generate_title từ session messages
        
        Args:
            session_messages: List of Message objects từ database
            
        Returns:
            Generated title
        """
        # Convert Message objects sang dicts
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
    """Get singleton instance của TitleGenerator"""
    global _title_generator
    if _title_generator is None:
        _title_generator = TitleGenerator()
    return _title_generator
