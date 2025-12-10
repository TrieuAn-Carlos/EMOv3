"""
Database setup for EMO chat sessions
SQLAlchemy ORM với SQLite database
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database path
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "sessions.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLAlchemy setup
Base = declarative_base()
engine = None
SessionLocal = None


class ChatSession(Base):
    """Model cho chat session"""
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True)
    title = Column(String, default="Cuộc trò chuyện mới")
    title_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    message_count = Column(Integer, default=0)
    # Study mode context: JSON with {"problem": str, "solution": str}
    study_context = Column(Text, nullable=True)
    
    # Relationship với messages
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.timestamp")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "title_generated": self.title_generated,
            "created_at": self.created_at.isoformat(),
            "message_count": self.message_count
        }


class Message(Base):
    """Model cho individual message"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationship với session
    session = relationship("ChatSession", back_populates="messages")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# SOCRATIQ MODELS
# =============================================================================

class Document(Base):
    """Model for uploaded PDF documents"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    page_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.now)
    
    # Relationship with quiz results
    quiz_results = relationship("QuizResult", back_populates="document", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "filename": self.filename,
            "page_count": self.page_count,
            "uploaded_at": self.uploaded_at.isoformat()
        }


class QuizResult(Base):
    """Model for quiz attempt results"""
    __tablename__ = "quiz_results"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=True)  # None if from highlight
    score = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    difficulty = Column(String, default="Beginner")  # Beginner, Intermediate, Advanced
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship with document
    document = relationship("Document", back_populates="quiz_results")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "score": self.score,
            "total_questions": self.total_questions,
            "difficulty": self.difficulty,
            "created_at": self.created_at.isoformat()
        }


class StudySession(Base):
    """Model for parent-child study sessions"""
    __tablename__ = "study_sessions"
    
    id = Column(String, primary_key=True)  # 6-char invite code (e.g., "ABC123")
    status = Column(String, default="pending")  # pending, active, completed
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    report = Column(Text, nullable=True)  # JSON: {summary, strengths, weaknesses, practice_problems}
    chat_session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "report": self.report,
            "chat_session_id": self.chat_session_id
        }


def init_db():
    """Initialize database - create tables if not exist"""
    global engine, SessionLocal
    
    # Ensure data directory exists
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Create engine with connection pooling
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        pool_pre_ping=True,  # Verify connections before using
        echo=False  # Set to True for SQL debug logging
    )
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Clear pending study sessions on startup
    db = SessionLocal()
    try:
        deleted = db.query(StudySession).filter(StudySession.status == "pending").delete()
        db.commit()
        if deleted > 0:
            print(f"🧹 Cleared {deleted} pending study session(s)")
    finally:
        db.close()
    
    print(f"✅ Database initialized at: {DB_PATH}")


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db():
    """Close database connections gracefully"""
    global engine
    if engine:
        engine.dispose()
        print("✅ Database connections closed")
