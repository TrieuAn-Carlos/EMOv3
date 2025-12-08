"""
EMO Backend - Email Router
Direct email fetch endpoints (bypass AI for speed)
"""

from fastapi import APIRouter, HTTPException, Query, Response
from utils.cache import get_cache

router = APIRouter()
cache = get_cache()


@router.get("/api/emails/list")
async def list_emails(
    response: Response,
    query: str = Query(default="newer_than:7d", description="Gmail search query"),
    max_results: int = Query(default=5, ge=1, le=20, description="Maximum emails to return")
):
    """
    List emails directly without AI processing.
    Bypasses AI for instant response (~500ms vs 5-8s).
    
    Cached for 5 minutes for instant repeat queries.
    
    Common queries:
    - "newer_than:7d" (default) - emails from last 7 days
    - "newer_than:1d" - today's emails
    - "from:john@example.com" - emails from specific sender
    """
    # Create cache key
    cache_key = f"email_list:{query}:{max_results}"
    
    # Try cache first
    cached_result = cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        return cached_result
    
    response.headers["X-Cache"] = "MISS"
    
    try:
        from integrations.gmail import quick_gmail_search
        
        result = quick_gmail_search(query, max_results)
        
        # Check for error messages
        if result.startswith("Error:") or result.startswith("No emails"):
            result_data = {
                "success": False,
                "content": result,
                "emails": []
            }
        else:
            result_data = {
                "success": True,
                "content": result,
                "query": query,
                "max_results": max_results
            }
        
        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, result_data, ttl=300)
        
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/email/{index}")
async def get_email_by_index(index: int, response: Response):
    """
    Fetch email content directly by index.
    Bypasses AI processing for instant response.
    
    Cached for 5 minutes for instant repeat access.
    """
    # Create cache key
    cache_key = f"email_detail:{index}"
    
    # Try cache first
    cached_result = cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        return cached_result
    
    response.headers["X-Cache"] = "MISS"
    
    try:
        from integrations.gmail import get_email_by_index as fetch_email
        
        result = fetch_email(index)
        
        # Check for error messages
        if result.startswith("Error:") or result.startswith("No recent"):
            raise HTTPException(status_code=400, detail=result)
        
        result_data = {
            "success": True,
            "content": result,
            "index": index
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result_data, ttl=300)
        
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
