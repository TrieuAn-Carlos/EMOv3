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
