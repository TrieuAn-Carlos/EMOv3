"""
Centralized LLM Configuration for EMO2
All LLM settings are defined here for consistency across the codebase.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# GEMINI CONFIGURATION
# =============================================================================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = 'gemini-2.5-flash'

# Generation settings
TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 4096

# Title generation settings (for chat history)
TITLE_MODEL = GEMINI_MODEL  # Use same model for title generation
TITLE_MAX_TOKENS = 50


# =============================================================================
# GEMINI MODEL INITIALIZATION
# =============================================================================

def get_gemini_model():
    """
    Get a configured Gemini model instance.
    Returns a GenerativeModel instance ready for use.
    """
    import google.generativeai as genai
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    generation_config = {
        "temperature": TEMPERATURE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }
    
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=generation_config,
    )
    
    return model


# =============================================================================
# CHROMADB MEMORY FUNCTIONS
# =============================================================================

import os
import threading

CHROMA_PATH = "./emo_memory"
_chroma_client = None
_chroma_collection = None
_chroma_lock = threading.Lock()


def get_chroma_collection():
    """
    Get or create the ChromaDB collection for memory storage.
    Thread-safe with retry logic.
    """
    global _chroma_client, _chroma_collection
    
    with _chroma_lock:
        if _chroma_collection is not None:
            return _chroma_collection
        
        try:
            import chromadb
            
            os.makedirs(CHROMA_PATH, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="emo_memory",
                metadata={"hnsw:space": "cosine"}
            )
            return _chroma_collection
        except Exception as e:
            print(f"Warning: Could not initialize ChromaDB: {e}")
            return None


def query_memory(query: str, n_results: int = 5):
    """
    Query the memory database for relevant documents.
    
    Args:
        query: Search query string
        n_results: Maximum number of results to return
        
    Returns:
        List of relevant memory documents
    """
    try:
        collection = get_chroma_collection()
        if collection is None or collection.count() == 0:
            return []
        
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count())
        )
        
        return results
    except Exception as e:
        print(f"Warning: Memory query failed: {e}")
        return []


def format_memories_for_context(memories) -> str:
    """
    Format memory query results for inclusion in chat context.
    
    Args:
        memories: Results from query_memory
        
    Returns:
        Formatted string of relevant memories
    """
    if not memories or not memories.get('documents'):
        return ""
    
    docs = memories.get('documents', [[]])[0]
    metas = memories.get('metadatas', [[]])[0]
    
    if not docs:
        return ""
    
    formatted = ["## Relevant Memories:"]
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        summary = meta.get('summary', meta.get('subject', ''))[:100]
        formatted.append(f"- {summary}: {doc[:200]}...")
    
    return "\n".join(formatted)
