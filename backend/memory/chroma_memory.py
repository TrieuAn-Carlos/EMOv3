"""
EMO Backend - Memory Module
============================
ChromaDB-based vector memory with singleton pattern.
Thread-safe initialization and querying.
"""

import os
import threading
from typing import Optional, Dict, List, Any

# Singleton pattern for ChromaDB
_chroma_client = None
_chroma_collection = None
_chroma_lock = threading.Lock()


def get_chroma_collection(chroma_path: str = None):
    """
    Get or create ChromaDB collection with thread-safe singleton.
    
    Args:
        chroma_path: Path to ChromaDB storage (default: from config)
        
    Returns:
        ChromaDB collection or None if initialization fails
    """
    global _chroma_client, _chroma_collection
    
    if chroma_path is None:
        from core.config import CHROMA_PATH
        chroma_path = CHROMA_PATH
    
    with _chroma_lock:
        if _chroma_collection is not None:
            return _chroma_collection
        
        try:
            import chromadb
            
            os.makedirs(chroma_path, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=chroma_path)
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="emo_memory",
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ ChromaDB initialized at: {chroma_path}")
            return _chroma_collection
        except Exception as e:
            print(f"❌ ChromaDB initialization failed: {e}")
            return None


def query_memory(query: str, n_results: int = 2) -> Optional[Dict[str, Any]]:
    """
    Query ChromaDB memory for relevant documents.
    
    Args:
        query: Search query string
        n_results: Maximum results to return (default 2 for speed)
        
    Returns:
        Query results dict or None if error
    """
    try:
        collection = get_chroma_collection()
        if collection is None or collection.count() == 0:
            return None
        
        # OPTIMIZATION: Limit results for faster queries
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            include=['documents', 'metadatas', 'distances']
        )
        
        return results
    except Exception as e:
        print(f"⚠️ Memory query failed: {e}")
        return None


def add_memory(
    document: str,
    metadata: Dict[str, Any],
    doc_id: Optional[str] = None
) -> bool:
    """
    Add a document to ChromaDB memory.
    
    Args:
        document: Text content to store
        metadata: Metadata dict (must include 'source' and 'summary')
        doc_id: Optional custom ID (auto-generated if None)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        collection = get_chroma_collection()
        if collection is None:
            return False
        
        if doc_id is None:
            import uuid
            from datetime import datetime
            doc_id = f"{metadata.get('source', 'doc')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        collection.add(
            documents=[document],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return True
    except Exception as e:
        print(f"⚠️ Memory add failed: {e}")
        return False


def format_memories_for_context(memories: Optional[Dict[str, Any]]) -> str:
    """
    Format memory query results for inclusion in context.
    
    Args:
        memories: Results from query_memory
        
    Returns:
        Formatted string for system prompt
    """
    if not memories or not memories.get('documents'):
        return ""
    
    docs = memories.get('documents', [[]])[0]
    metas = memories.get('metadatas', [[]])[0]
    
    if not docs:
        return ""
    
    formatted = ["## Relevant Memories:"]
    for i, doc in enumerate(docs[:3]):
        meta = metas[i] if i < len(metas) else {}
        summary = meta.get('summary', meta.get('subject', ''))[:80]
        formatted.append(f"- {summary}: {doc[:150]}...")
    
    return "\n".join(formatted)


def get_memory_stats() -> Dict[str, Any]:
    """
    Get statistics about memory collection.
    
    Returns:
        Dict with count and collection info
    """
    try:
        collection = get_chroma_collection()
        if collection is None:
            return {"status": "not_initialized", "count": 0}
        
        count = collection.count()
        return {
            "status": "ready",
            "count": count,
            "collection_name": collection.name
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "count": 0}
