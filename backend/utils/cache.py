"""
Simple in-memory cache with TTL (Time To Live)
"""

import time
from typing import Any, Optional
from functools import wraps


class SimpleCache:
    """Thread-safe in-memory cache with TTL."""
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        if time.time() > expiry:
            # Expired, remove it
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL (default 5 minutes)."""
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
    
    def clear(self):
        """Clear all cache."""
        self._cache.clear()
    
    def delete(self, key: str):
        """Delete specific key."""
        if key in self._cache:
            del self._cache[key]


# Global cache instance
_cache = SimpleCache()


def cached(ttl: int = 300):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and args
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            result = _cache.get(cache_key)
            if result is not None:
                return result
            
            # Cache miss, call function
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def get_cache():
    """Get global cache instance."""
    return _cache
