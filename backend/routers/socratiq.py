"""
SocratiQ - API Router
=====================
FastAPI endpoints for PDF document upload and quiz generation.
"""

import os
import uuid
import shutil
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, Document, QuizResult
from services.document_service import ingest_pdf, get_page_content, delete_document
from agent.socratiq_agent import generate_quiz, generate_quiz_for_search, generate_quiz_from_image


router = APIRouter()

# Temp upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class QuizRequest(BaseModel):
    """Request body for quiz generation."""
    doc_id: str = Field(..., description="Document ID")
    page: Optional[int] = Field(None, description="Page number (1-indexed)")
    context: Optional[str] = Field(None, description="Highlighted text context")
    difficulty: str = Field("Beginner", description="Beginner, Intermediate, or Advanced")
    num_questions: int = Field(5, ge=1, le=10, description="Number of questions")


class QuizResponse(BaseModel):
    """Response for quiz generation."""
    quiz_id: str
    title: str
    difficulty: str
    questions: List[dict]
    doc_id: str
    page_number: Optional[int]
    source: str  # "page" or "highlight"


class DocumentResponse(BaseModel):
    """Response for document operations."""
    id: str
    filename: str
    page_count: int
    uploaded_at: str


class SubmitQuizRequest(BaseModel):
    """Request body for submitting quiz answers."""
    quiz_id: str = Field(..., description="Quiz result ID")
    answers: List[str] = Field(..., description="List of selected answers (A, B, C, D)")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest a PDF document.
    
    - Extracts text page-by-page with overlap
    - Stores chunks in ChromaDB for semantic retrieval
    - Saves metadata in SQLite
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Save to temp location
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.pdf")
    
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Ingest PDF
        result = ingest_pdf(temp_path, file.filename)
        
        # Keep PDF file with doc_id as name for later serving
        final_path = os.path.join(UPLOAD_DIR, f"{result['id']}.pdf")
        shutil.move(temp_path, final_path)
        
        # Save to database
        doc = Document(
            id=result["id"],
            filename=result["filename"],
            page_count=result["page_count"],
            uploaded_at=datetime.now()
        )
        db.add(doc)
        db.commit()
        
        return DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            page_count=doc.page_count,
            uploaded_at=doc.uploaded_at.isoformat()
        )
        
    except Exception as e:
        # Cleanup on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents."""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            page_count=doc.page_count,
            uploaded_at=doc.uploaded_at.isoformat()
        )
        for doc in docs
    ]


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Get document details."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        page_count=doc.page_count,
        uploaded_at=doc.uploaded_at.isoformat()
    )


@router.get("/documents/{doc_id}/file")
async def get_document_file(doc_id: str, db: Session = Depends(get_db)):
    """Serve the original PDF file for rendering."""
    from fastapi.responses import FileResponse
    
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    pdf_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        pdf_path, 
        media_type="application/pdf",
        filename=doc.filename
    )


@router.delete("/documents/{doc_id}")
async def delete_document_endpoint(doc_id: str, db: Session = Depends(get_db)):
    """Delete a document and its ChromaDB chunks."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from ChromaDB
    delete_document(doc_id)
    
    # Delete PDF file
    pdf_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    
    # Delete from database
    db.delete(doc)
    db.commit()
    
    return {"status": "deleted", "doc_id": doc_id}


@router.get("/documents/{doc_id}/page/{page_number}")
async def get_page(doc_id: str, page_number: int, db: Session = Depends(get_db)):
    """Get content for a specific page."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if page_number < 1 or page_number > doc.page_count:
        raise HTTPException(status_code=400, detail=f"Page must be between 1 and {doc.page_count}")
    
    content = get_page_content(doc_id, page_number)
    if not content:
        raise HTTPException(status_code=404, detail="Page content not found")
    
    return {
        "doc_id": doc_id,
        "page_number": page_number,
        "total_pages": doc.page_count,
        "content": content
    }


@router.post("/documents/quiz", response_model=QuizResponse)
async def generate_quiz_endpoint(
    request: QuizRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a quiz from document content.
    
    Modes:
    - **Page Mode**: Provide `page` number to quiz on that page
    - **Highlight Mode**: Provide `context` with selected text
    """
    # Validate document exists
    doc = db.query(Document).filter(Document.id == request.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Validate page if provided
    if request.page and (request.page < 1 or request.page > doc.page_count):
        raise HTTPException(
            status_code=400, 
            detail=f"Page must be between 1 and {doc.page_count}"
        )
    
    # Must have either page or context
    if not request.page and not request.context:
        raise HTTPException(
            status_code=400,
            detail="Either 'page' or 'context' must be provided"
        )
    
    try:
        if request.page and not request.context:
            # Vision mode: send PDF page as image
            pdf_path = os.path.join(UPLOAD_DIR, f"{request.doc_id}.pdf")
            if not os.path.exists(pdf_path):
                raise HTTPException(status_code=404, detail="PDF file not found")
            
            quiz_data = generate_quiz_from_image(
                pdf_path=pdf_path,
                page_number=request.page,
                difficulty=request.difficulty,
                num_questions=request.num_questions
            )
            quiz_data["doc_id"] = request.doc_id
        else:
            # Text mode: use highlighted text context
            quiz_data = generate_quiz(
                doc_id=request.doc_id,
                page_number=request.page,
                context=request.context,
                difficulty=request.difficulty,
                num_questions=request.num_questions
            )
        
        # Create quiz result record
        quiz_id = str(uuid.uuid4())[:8]
        quiz_result = QuizResult(
            id=quiz_id,
            document_id=request.doc_id,
            page_number=request.page,
            difficulty=request.difficulty,
            total_questions=len(quiz_data.get("questions", [])),
            score=0  # Will be updated when submitted
        )
        db.add(quiz_result)
        db.commit()
        
        return QuizResponse(
            quiz_id=quiz_id,
            title=quiz_data.get("title", "Quiz"),
            difficulty=quiz_data.get("difficulty", request.difficulty),
            questions=quiz_data.get("questions", []),
            doc_id=request.doc_id,
            page_number=request.page,
            source=quiz_data.get("source", "vision" if (request.page and not request.context) else "text")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")


@router.post("/documents/quiz/submit")
async def submit_quiz(request: SubmitQuizRequest, db: Session = Depends(get_db)):
    """Submit quiz answers and calculate score."""
    quiz_result = db.query(QuizResult).filter(QuizResult.id == request.quiz_id).first()
    if not quiz_result:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # For now, we don't have the correct answers stored
    # In a full implementation, you'd store the quiz and validate answers
    quiz_result.score = len([a for a in request.answers if a])  # Placeholder
    db.commit()
    
    return {
        "quiz_id": request.quiz_id,
        "score": quiz_result.score,
        "total": quiz_result.total_questions
    }


@router.get("/documents/{doc_id}/quiz-history")
async def get_quiz_history(doc_id: str, db: Session = Depends(get_db)):
    """Get quiz history for a document."""
    results = db.query(QuizResult).filter(
        QuizResult.document_id == doc_id
    ).order_by(QuizResult.created_at.desc()).all()
    
    return [r.to_dict() for r in results]
