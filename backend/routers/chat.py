"""
EMO Backend - Chat Router
=========================
Handles chat messages and streaming responses.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent.gemma_function_calling import chat_with_gemma, stream_chat_with_gemma
from database import get_db
from services.session_service import SessionService
from services.title_generator import get_title_generator


router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = None
    context: Optional[str] = ""


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    tools_used: list[str] = []
    thinking: Optional[str] = None


class TitleRequest(BaseModel):
    """Request model for title generation."""
    messages: list[dict]  # [{"role": "user", "content": "..."}, ...]


class TitleResponse(BaseModel):
    """Response model for title generation."""
    title: str


class SessionResponse(BaseModel):
    """Response model for session."""
    id: str
    title: str
    title_generated: bool
    created_at: str
    message_count: int


class SessionDetailResponse(BaseModel):
    """Response model for session with messages."""
    id: str
    title: str
    title_generated: bool
    created_at: str
    message_count: int
    messages: list[dict]  # [{"role": "user", "content": "...", "timestamp": "..."}, ...]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Send a message and get a response from EMO.
    
    Uses Gemma 3 27B with manual function calling.
    """
    try:
        # Use Gemma 3 27B with manual function calling
        result = await chat_with_gemma(
            user_message=request.message,
            session_id=request.session_id,
            db=db,
            )
        
        return ChatResponse(
            response=result.get("response", ""),
            tools_used=result.get("tools_used", []),
            thinking=result.get("thinking"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def chat_stream(message: str, session_id: Optional[str] = None, mode: Optional[str] = None, debug: bool = False, db: Session = Depends(get_db)):
    """
    Stream a chat response using Server-Sent Events (SSE).
    
    Query params:
        message: The user's message
        session_id: Optional session ID for context (auto-created if not provided)
        mode: Optional mode ('study' for Socratic teaching)
        debug: If true, include debug info in response
    
    Returns:
        SSE stream with JSON chunks
    """
    async def generate():
        try:
            # Auto-create session if not provided
            actual_session_id = session_id
            if not actual_session_id:
                service = SessionService(db)
                new_session = service.create_session()
                actual_session_id = new_session.id
                # Send session_id to frontend
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': actual_session_id}, ensure_ascii=False)}\n\n"
            
            async for chunk in stream_chat_with_gemma(message, actual_session_id, db, mode, debug):
                # Format as SSE
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
            
            # Send done signal
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat/generate-title", response_model=TitleResponse)
async def generate_title(request: TitleRequest):
    """
    Generate a concise title for a chat session based on messages.
    Uses configured LLM via TitleGenerator.
    """
    try:
        # Use centralized TitleGenerator
        title_gen = get_title_generator()
        
        # Convert request messages (dicts) to whatever TitleGenerator expects
        # TitleGenerator expects list of dicts with role/content, which matches request structure
        title = title_gen.generate_title(request.messages)
        
        return TitleResponse(title=title)
        
    except Exception as e:
        # Fallback to generic title on error
        print(f"Generate title endpoint error: {e}")
        return TitleResponse(title="New Chat")


# =============================================================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/sessions", response_model=SessionResponse)
async def create_session(db: Session = Depends(get_db)):
    """
    Create a new chat session.
    
    Returns:
        New session with generated ID
    """
    try:
        service = SessionService(db)
        session = service.create_session()
        
        return SessionResponse(
            id=session.id,
            title=session.title,
            title_generated=session.title_generated,
            created_at=session.created_at.isoformat(),
            message_count=session.message_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=dict)
async def list_sessions(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """
    List all chat sessions.
    
    Query params:
        limit: Maximum number of sessions to return (default 50)
        offset: Offset for pagination (default 0)
    """
    try:
        service = SessionService(db)
        sessions = service.list_sessions(limit=limit, offset=offset)
        
        session_list = [
            {
                "id": session.id,
                "title": session.title,
                "title_generated": session.title_generated,
                "created_at": session.created_at.isoformat(),
                "message_count": session.message_count,
            }
            for session in sessions
        ]
        
        return {"sessions": session_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, db: Session = Depends(get_db)):
    """
    Get a specific session with all messages.
    
    Path params:
        session_id: The session ID
    """
    try:
        service = SessionService(db)
        session = service.get_session(session_id, include_messages=True)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in session.messages
        ]
        
        return SessionDetailResponse(
            id=session.id,
            title=session.title,
            title_generated=session.title_generated,
            created_at=session.created_at.isoformat(),
            message_count=session.message_count,
            messages=messages
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """
    Delete a session and all its messages.
    
    Path params:
        session_id: The session ID to delete
    """
    try:
        service = SessionService(db)
        success = service.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/close", response_model=TitleResponse)
async def close_session(session_id: str, db: Session = Depends(get_db)):
    """
    Close a session and generate title if needed.
    Call this when user closes a chat tab.
    
    Path params:
        session_id: The session ID to close
    """
    try:
        service = SessionService(db)
        
        # Check if should generate title
        should_generate, messages = service.should_generate_title(session_id)
        
        if not should_generate:
            session = service.get_session(session_id, include_messages=False)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return TitleResponse(title=session.title)
        
        # Generate title using TitleGenerator
        title_gen = get_title_generator()
        new_title = title_gen.generate_title_from_session(messages)
        
        # Update session with new title
        service.update_session_title(session_id, new_title)
        
        return TitleResponse(title=new_title)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
