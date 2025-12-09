"""
EMO Backend - Memory Tools
===========================
LangChain tools for memory operations.
"""

from langchain_core.tools import tool
from typing import Optional
from datetime import datetime
import uuid

from .chroma_memory import (
    query_memory as _query_memory,
    add_memory as _add_memory,
    get_chroma_collection,
)


@tool
def search_memory(query: str) -> str:
    """
    Search through stored memories for relevant information.
    
    Use this to find previously saved emails, web pages, or documents.
    Returns summaries of matching memories with relevance scores.
    
    Args:
        query: Natural language search query
    
    Returns:
        Formatted list of relevant memories
    """
    try:
        collection = get_chroma_collection()
        if collection is None:
            return "❌ Memory not initialized. Use tools to save information first."
        
        if collection.count() == 0:
            return "📭 Memory is empty. No documents have been saved yet."
        
        results = _query_memory(query, n_results=5)
        
        if not results or not results.get('documents') or not results['documents'][0]:
            return "🔍 No relevant memories found for your query."
        
        # Format results
        output_parts = [f"**Found {len(results['documents'][0])} relevant memories:**\n"]
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            relevance = max(0, round((1 - distance) * 100))
            summary = metadata.get('summary', doc[:100])
            source = metadata.get('source', 'Unknown')
            doc_id = results['ids'][0][i-1]
            
            output_parts.append(f"**[{i}]** [{relevance}% match] {summary}")
            output_parts.append(f"   📍 Source: {source} | ID: `{doc_id}`\n")
        
        output_parts.append("💡 Use `recall_memory(doc_id)` to get full content.")
        
        return "\n".join(output_parts)
    
    except Exception as e:
        return f"❌ Error searching memory: {str(e)[:100]}"


@tool
def recall_memory(doc_id: str) -> str:
    """
    Retrieve the full content of a specific memory by its document ID.
    
    Use this after search_memory to get complete details.
    
    Args:
        doc_id: Document ID from search results
        
    Returns:
        Full document content with metadata
    """
    try:
        collection = get_chroma_collection()
        if collection is None:
            return "❌ Memory not initialized."
        
        result = collection.get(ids=[doc_id], include=['documents', 'metadatas'])
        
        if not result or not result['documents']:
            return f"❌ Memory with ID `{doc_id}` not found."
        
        doc = result['documents'][0]
        meta = result['metadatas'][0] if result['metadatas'] else {}
        
        output = [
            f"**📄 Memory: {meta.get('summary', 'Document')}**",
            f"**📍 Source:** {meta.get('source', 'Unknown')}",
            f"**📅 Date:** {meta.get('date', 'N/A')}",
            "",
            "**Content:**",
            doc
        ]
        
        return "\n".join(output)
    
    except Exception as e:
        return f"❌ Error retrieving memory: {str(e)[:100]}"


@tool
def save_long_term_memory(fact: str, category: str = "other") -> str:
    """
    Save a personal fact to long-term memory (permanent).
    
    Use when user explicitly asks to remember something important.
    Categories: "identity", "preference", "relationship", "date", "skill", "other"
    
    Args:
        fact: The information to remember
        category: Category of information
        
    Returns:
        Confirmation message
    """
    try:
        doc_id = f"longterm_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        metadata = {
            "source": "user_conversation",
            "category": category,
            "summary": fact[:100],
            "date": datetime.now().isoformat(),
            "type": "long_term_fact"
        }
        
        success = _add_memory(fact, metadata, doc_id)
        
        if success:
            # Also update user_config.json for persistent identity facts
            if category in ["identity", "preference"]:
                from core.config import USER_CONFIG_FILE
                import json
                
                config = {}
                if USER_CONFIG_FILE.exists():
                    with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                
                if 'long_term_facts' not in config:
                    config['long_term_facts'] = {}
                if category not in config['long_term_facts']:
                    config['long_term_facts'][category] = []
                
                config['long_term_facts'][category].append(fact)
                
                with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            
            return f"✅ Đã lưu vào bộ nhớ dài hạn (category: {category}): {fact[:80]}..."
        else:
            return "❌ Không thể lưu vào bộ nhớ."
    
    except Exception as e:
        return f"❌ Lỗi khi lưu bộ nhớ: {str(e)[:100]}"


@tool
def query_long_term(query: str) -> str:
    """
    Search long-term personal facts about the user.
    
    Use when user asks about previously shared personal information.
    
    Args:
        query: What to search for
        
    Returns:
        Relevant personal facts
    """
    try:
        results = _query_memory(query, n_results=3)
        
        if not results or not results.get('documents') or not results['documents'][0]:
            return "🤔 Không tìm thấy thông tin cá nhân liên quan."
        
        # Filter for long-term facts only
        output_parts = ["**Thông tin cá nhân đã lưu:**\n"]
        found_any = False
        
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            if meta.get('type') == 'long_term_fact':
                found_any = True
                category = meta.get('category', 'other')
                output_parts.append(f"- **{category.title()}**: {doc}")
        
        if not found_any:
            return "🤔 Không tìm thấy thông tin cá nhân liên quan."
        
        return "\n".join(output_parts)
    
    except Exception as e:
        return f"❌ Lỗi khi tìm kiếm: {str(e)[:100]}"
