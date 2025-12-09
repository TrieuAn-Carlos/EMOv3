"""
Session Service - CRUD operations cho chat sessions
Clean service layer cho session management
"""

from sqlalchemy.orm import Session
from database import ChatSession, Message
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid

# Constants
MAX_MESSAGES_PER_SESSION = 30
WARNING_THRESHOLD = 25  # Show warning at 25/30 messages


class SessionService:
    """Service class cho session management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """
        Tạo session mới
        
        Args:
            session_id: Optional custom ID, generate UUID nếu không có
            
        Returns:
            ChatSession object
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session = ChatSession(
            id=session_id,
            title="Cuộc trò chuyện mới",
            title_generated=False,
            created_at=datetime.now(),
            message_count=0
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_session(self, session_id: str, include_messages: bool = True) -> Optional[ChatSession]:
        """
        Lấy session by ID
        
        Args:
            session_id: Session ID
            include_messages: Có load messages không (default True)
            
        Returns:
            ChatSession object hoặc None nếu không tìm thấy
        """
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        if session and include_messages:
            # Eager load messages (already handled by relationship)
            _ = session.messages
        
        return session
    
    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[ChatSession]:
        """
        List tất cả sessions, sorted by created_at desc
        
        Args:
            limit: Max number of sessions to return
            offset: Offset for pagination
            
        Returns:
            List of ChatSession objects
        """
        return (
            self.db.query(ChatSession)
            .order_by(ChatSession.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def delete_session(self, session_id: str) -> bool:
        """
        Xóa session và tất cả messages
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        session = self.get_session(session_id, include_messages=False)
        
        if not session:
            return False
        
        self.db.delete(session)
        self.db.commit()
        
        return True
    
    def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        auto_create_session: bool = True
    ) -> Dict:
        """
        Save message vào session
        
        Args:
            session_id: Session ID
            role: "user" hoặc "assistant"
            content: Message content
            auto_create_session: Tự động tạo session nếu không tồn tại
            
        Returns:
            Dict với status và metadata:
            {
                "saved": bool,
                "count": int,
                "warning": {"message": str, "type": "warning"|"error"} | None,
                "limit_reached": bool
            }
        """
        # Get or create session
        session = self.get_session(session_id, include_messages=False)
        
        if not session:
            if auto_create_session:
                session = self.create_session(session_id)
            else:
                return {
                    "saved": False,
                    "count": 0,
                    "warning": {
                        "message": "Session không tồn tại",
                        "type": "error"
                    },
                    "limit_reached": False
                }
        
        # Check limit
        if session.message_count >= MAX_MESSAGES_PER_SESSION:
            return {
                "saved": False,
                "count": session.message_count,
                "warning": {
                    "message": "Bạn cần tạo cuộc trò chuyện mới để tiếp tục nhé!",
                    "type": "error"
                },
                "limit_reached": True
            }
        
        # Save message
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        
        self.db.add(message)
        
        # Update session message count
        session.message_count += 1
        self.db.commit()
        
        # Prepare response with warning if needed
        warning = None
        if session.message_count >= WARNING_THRESHOLD:
            warning = {
                "message": f"Bạn sắp hết chỗ trò chuyện rồi! ({session.message_count}/{MAX_MESSAGES_PER_SESSION} tin nhắn)",
                "type": "warning"
            }
        
        return {
            "saved": True,
            "count": session.message_count,
            "warning": warning,
            "limit_reached": False
        }
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """
        Lấy messages của session
        
        Args:
            session_id: Session ID
            limit: Optional limit số messages (lấy newest first)
            
        Returns:
            List of Message objects, ordered by timestamp asc
        """
        query = (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.timestamp.asc())
        )
        
        if limit:
            # Get last N messages
            query = query.limit(limit)
        
        return query.all()
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """
        Update session title
        
        Args:
            session_id: Session ID
            title: New title
            
        Returns:
            True nếu success, False nếu session không tồn tại
        """
        session = self.get_session(session_id, include_messages=False)
        
        if not session:
            return False
        
        session.title = title
        session.title_generated = True
        self.db.commit()
        
        return True
    
    def should_generate_title(self, session_id: str) -> Tuple[bool, Optional[List[Message]]]:
        """
        Check xem có nên generate title không
        
        Args:
            session_id: Session ID
            
        Returns:
            Tuple of (should_generate: bool, messages: List[Message] | None)
        """
        session = self.get_session(session_id, include_messages=False)
        
        if not session:
            return False, None
        
        # Đã generate title rồi thì skip
        if session.title_generated:
            return False, None
        
        # Chưa đủ 3 messages thì chưa generate
        if session.message_count < 3:
            return False, None
        
        # Get messages để generate title
        messages = self.get_session_messages(session_id, limit=5)  # Lấy 5 messages đầu
        
        return True, messages

    def auto_generate_title_if_needed(self, session_id: str) -> Optional[str]:
        """
        Tự động generate title nếu đủ điều kiện (3+ messages, chưa có title)
        
        Args:
            session_id: Session ID
            
        Returns:
            Generated title nếu có, None nếu không cần generate
        """
        should_generate, messages = self.should_generate_title(session_id)
        
        if not should_generate or not messages:
            return None
        
        try:
            from services.title_generator import get_title_generator
            title_gen = get_title_generator()
            new_title = title_gen.generate_title_from_session(messages)
            
            # Update session với title mới
            self.update_session_title(session_id, new_title)
            print(f"✅ Auto-generated title: '{new_title}' for session {session_id[:8]}...")
            
            return new_title
        except Exception as e:
            print(f"⚠️ Auto title generation failed: {e}")
            return None
