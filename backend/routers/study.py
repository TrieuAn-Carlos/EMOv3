"""
EMO Backend - Study Session Router
===================================
API endpoints for parent-child study session management.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, StudySession, ChatSession, Message

router = APIRouter()


class CreateSessionRequest(BaseModel):
    topic: str
    child_name: str = "Josh"


class SessionResponse(BaseModel):
    id: str
    topic: str
    child_name: str
    status: str
    created_at: str


# =============================================================================
# PENDING INVITE (Child polls this)
# =============================================================================

@router.get("/pending")
def get_pending_invite(db: Session = Depends(get_db)):
    """
    Get pending study session invite for child.
    Child's frontend polls this every 2 seconds.
    """
    session = db.query(StudySession).filter(
        StudySession.status == "pending"
    ).order_by(StudySession.created_at.desc()).first()
    
    if not session:
        return {"invite": None}
    
    return {
        "invite": {
            "id": session.id,
            "topic": session.report,  # We store topic in report field temporarily
            "created_at": session.created_at.isoformat()
        }
    }


# =============================================================================
# CREATE SESSION (Emo tool calls this internally)
# =============================================================================

@router.post("/create")
def create_session(request: CreateSessionRequest, db: Session = Depends(get_db)):
    """Create a new study session."""
    import uuid
    
    session_id = str(uuid.uuid4())[:8]
    
    # Store topic in report field temporarily (will be replaced with actual report)
    session = StudySession(
        id=session_id,
        status="pending",
        report=request.topic  # Using report field to store topic for now
    )
    
    db.add(session)
    db.commit()
    
    return {
        "id": session_id,
        "topic": request.topic,
        "child_name": request.child_name,
        "status": "pending"
    }


# =============================================================================
# ACCEPT SESSION (Child clicks button)
# =============================================================================

@router.post("/accept/{session_id}")
def accept_session(session_id: str, db: Session = Depends(get_db)):
    """Child accepts the study session invite."""
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "pending":
        raise HTTPException(status_code=400, detail="Session already started or completed")
    
    # Create a chat session for the study
    import uuid
    chat_session_id = str(uuid.uuid4())
    chat_session = ChatSession(
        id=chat_session_id,
        title=f"Study: {session.report}"  # topic stored in report
    )
    db.add(chat_session)
    
    # Update study session
    session.status = "active"
    session.chat_session_id = chat_session_id
    db.commit()
    
    return {
        "id": session_id,
        "topic": session.report,
        "status": "active",
        "chat_session_id": chat_session_id
    }


# =============================================================================
# COMPLETE SESSION (Child finishes studying)
# =============================================================================

@router.post("/complete/{session_id}")
def complete_session(session_id: str, db: Session = Depends(get_db)):
    """Mark study session as completed and generate report."""
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    topic = session.report  # Get topic before overwriting
    
    # Generate simple report
    import json
    report = {
        "summary": f"Josh completed a study session on {topic}.",
        "duration": "15 minutes",
        "topics_covered": [topic],
        "strengths": ["Active engagement", "Good questions"],
        "weaknesses": ["Needs more practice"],
        "accuracy": 75,
        "practice_problems": [
            {"question": f"Practice problem on {topic} #1", "topic": topic},
            {"question": f"Practice problem on {topic} #2", "topic": topic}
        ]
    }
    
    session.status = "completed"
    session.completed_at = datetime.now()
    session.report = json.dumps(report)
    db.commit()
    
    return {
        "id": session_id,
        "status": "completed",
        "message": "Session completed! Report is ready."
    }


# =============================================================================
# GET REPORT (Parent asks for report)
# =============================================================================

@router.get("/report/{session_id}")
def get_report(session_id: str, db: Session = Depends(get_db)):
    """Get the study session report."""
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "completed":
        return {"report": None, "message": "Session not completed yet"}
    
    import json
    try:
        report = json.loads(session.report)
    except:
        report = {"summary": "Report generation failed"}
    
    return {
        "id": session_id,
        "status": session.status,
        "report": report
    }


# =============================================================================
# GET ACTIVE SESSION (For child to check current session)
# =============================================================================

@router.get("/active")
def get_active_session(db: Session = Depends(get_db)):
    """Get the currently active study session."""
    session = db.query(StudySession).filter(
        StudySession.status == "active"
    ).order_by(StudySession.created_at.desc()).first()
    
    if not session:
        return {"session": None}
    
    return {
        "session": {
            "id": session.id,
            "topic": session.report if session.status == "pending" else "Study Session",
            "status": session.status,
            "chat_session_id": session.chat_session_id
        }
    }
