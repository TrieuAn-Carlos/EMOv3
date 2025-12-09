"""
SocratiQ - PDF Document Ingestion Service
==========================================
Handles PDF upload, text extraction, chunking with overlap, and ChromaDB storage.
"""

import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pypdf import PdfReader
import chromadb
from chromadb.config import Settings

# ChromaDB setup
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chromadb")
os.makedirs(CHROMA_DIR, exist_ok=True)

# Initialize ChromaDB client
_chroma_client = None
_collection = None


def get_chroma_client():
    """Get or create ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _chroma_client


def get_collection():
    """Get or create the SocratiQ documents collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name="socratiq_docs",
            metadata={"description": "SocratiQ PDF document chunks for quiz generation"}
        )
    return _collection


# =============================================================================
# PDF PROCESSING
# =============================================================================

OVERLAP_CHARS = 200  # Characters to overlap between pages


def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from PDF page by page with overlap context.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        List of dicts with page_number and text content
    """
    reader = PdfReader(file_path)
    pages = []
    prev_page_tail = ""
    
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        
        # Add overlap from previous page
        if prev_page_tail:
            page_text = f"[Context from previous page: {prev_page_tail}]\n\n{page_text}"
        
        pages.append({
            "page_number": i + 1,  # 1-indexed
            "text": page_text.strip()
        })
        
        # Store tail for next page's overlap
        if len(page_text) > OVERLAP_CHARS:
            prev_page_tail = page_text[-OVERLAP_CHARS:]
        else:
            prev_page_tail = page_text
    
    return pages


def ingest_pdf(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Ingest a PDF file: extract text and store in ChromaDB.
    
    Args:
        file_path: Path to the uploaded PDF file
        filename: Original filename
        
    Returns:
        Document metadata dict with id, filename, page_count
    """
    # Generate document ID
    doc_id = str(uuid.uuid4())[:8]
    
    # Extract text from all pages
    pages = extract_text_from_pdf(file_path)
    
    if not pages:
        raise ValueError("Could not extract any text from PDF")
    
    # Store in ChromaDB
    collection = get_collection()
    
    # Prepare data for ChromaDB
    ids = []
    documents = []
    metadatas = []
    
    for page in pages:
        chunk_id = f"{doc_id}_page_{page['page_number']}"
        ids.append(chunk_id)
        documents.append(page["text"])
        metadatas.append({
            "doc_id": doc_id,
            "page": page["page_number"],
            "filename": filename
        })
    
    # Add to collection
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    
    print(f"✅ Ingested PDF '{filename}' with {len(pages)} pages (doc_id: {doc_id})")
    
    return {
        "id": doc_id,
        "filename": filename,
        "page_count": len(pages)
    }


# =============================================================================
# CONTENT RETRIEVAL
# =============================================================================

def get_page_content(doc_id: str, page_number: int) -> Optional[str]:
    """
    Retrieve content for a specific page from ChromaDB.
    
    Args:
        doc_id: Document ID
        page_number: Page number (1-indexed)
        
    Returns:
        Page text content or None if not found
    """
    collection = get_collection()
    
    results = collection.get(
        ids=[f"{doc_id}_page_{page_number}"],
        include=["documents"]
    )
    
    if results and results["documents"]:
        return results["documents"][0]
    
    return None


def get_document_pages(doc_id: str) -> List[Dict[str, Any]]:
    """
    Get all pages for a document.
    
    Args:
        doc_id: Document ID
        
    Returns:
        List of page dicts with page_number and text
    """
    collection = get_collection()
    
    results = collection.get(
        where={"doc_id": doc_id},
        include=["documents", "metadatas"]
    )
    
    pages = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"]):
            pages.append({
                "page_number": results["metadatas"][i]["page"],
                "text": doc
            })
    
    # Sort by page number
    pages.sort(key=lambda x: x["page_number"])
    return pages


def search_content(doc_id: str, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Semantic search within a document.
    
    Args:
        doc_id: Document ID
        query: Search query
        n_results: Number of results to return
        
    Returns:
        List of matching page chunks with scores
    """
    collection = get_collection()
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where={"doc_id": doc_id},
        include=["documents", "metadatas", "distances"]
    )
    
    matches = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            matches.append({
                "page_number": results["metadatas"][0][i]["page"],
                "text": doc,
                "distance": results["distances"][0][i] if results["distances"] else None
            })
    
    return matches


def delete_document(doc_id: str) -> bool:
    """
    Delete a document and all its pages from ChromaDB.
    
    Args:
        doc_id: Document ID
        
    Returns:
        True if deleted, False if not found
    """
    collection = get_collection()
    
    # Get all chunk IDs for this document
    results = collection.get(
        where={"doc_id": doc_id},
        include=["metadatas"]
    )
    
    if not results or not results["ids"]:
        return False
    
    # Delete all chunks
    collection.delete(ids=results["ids"])
    print(f"🗑️ Deleted document {doc_id} ({len(results['ids'])} chunks)")
    
    return True
