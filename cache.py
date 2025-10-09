"""
Light caching module for Phase 4.
Provides simple in-memory caching with TTL for expensive operations.
"""

import time
from functools import wraps
from typing import Any, Dict

# Simple in-memory cache with TTL
_cache: Dict[str, Dict[str, Any]] = {}

def cached(ttl_seconds: int = 60):
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl_seconds: Time to live in seconds
        
    Usage:
        @cached(ttl_seconds=60)
        def expensive_function(arg1, arg2):
            return compute_expensive_result()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Check if cached result exists and is still valid
            if cache_key in _cache:
                cached_data = _cache[cache_key]
                if time.time() - cached_data['timestamp'] < ttl_seconds:
                    return cached_data['value']
                else:
                    # Expired, remove from cache
                    del _cache[cache_key]
            
            # Compute result and cache it
            result = func(*args, **kwargs)
            _cache[cache_key] = {
                'value': result,
                'timestamp': time.time()
            }
            
            return result
        return wrapper
    return decorator

def invalidate_cache(pattern: str = None):
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: If provided, only invalidate entries containing this pattern.
                If None, invalidate all entries.
    """
    if pattern:
        keys_to_remove = [key for key in _cache.keys() if pattern in key]
        for key in keys_to_remove:
            del _cache[key]
    else:
        _cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for debugging."""
    return {
        'total_entries': len(_cache),
        'entries': list(_cache.keys()),
        'memory_usage_estimate': sum(len(str(v)) for v in _cache.values())
    }
