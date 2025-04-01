import logging
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable, Tuple, TypeVar
from datetime import datetime, timedelta
from threading import RLock
import functools

logger = logging.getLogger(__name__)

# Type variable for generic return types
T = TypeVar('T')

class CacheService:
    """Service for caching frequently accessed data to improve performance."""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize the cache service.
        
        Args:
            ttl_seconds: Default time-to-live for cache entries in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = ttl_seconds
        self.locks: Dict[str, RLock] = {}
        self.master_lock = RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        now = time.time()
        
        # Check if entry is expired
        if entry['expiry'] < now:
            self._remove(key)
            return None
            
        # Update access time
        entry['last_access'] = now
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl_seconds: Optional TTL override in seconds
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()
        
        entry = {
            'value': value,
            'expiry': now + ttl,
            'created': now,
            'last_access': now
        }
        
        with self._get_lock(key):
            self.cache[key] = entry
    
    def delete(self, key: str) -> None:
        """
        Delete a specific cache entry.
        
        Args:
            key: The cache key to delete
        """
        self._remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.master_lock:
            self.cache.clear()
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all cache entries matching a pattern.
        
        Args:
            pattern: String pattern to match (simple contains check)
            
        Returns:
            Number of entries cleared
        """
        keys_to_remove = []
        
        # Find all matching keys
        with self.master_lock:
            for key in self.cache.keys():
                if pattern in key:
                    keys_to_remove.append(key)
        
        # Remove matching keys
        for key in keys_to_remove:
            self._remove(key)
            
        return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        now = time.time()
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() if entry['expiry'] < now)
        
        # Calculate size estimation
        size_bytes = 0
        for key, entry in self.cache.items():
            size_bytes += len(key)
            try:
                size_bytes += len(json.dumps(entry['value']))
            except:
                # If value can't be JSON serialized, use string representation
                size_bytes += len(str(entry['value']))
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'size_bytes': size_bytes,
            'size_mb': size_bytes / (1024 * 1024)
        }
    
    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key from prefix and arguments.
        
        Args:
            prefix: Key prefix (usually function or resource name)
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            Generated cache key
        """
        # Convert args and kwargs to a string
        args_str = json.dumps(args, sort_keys=True)
        kwargs_str = json.dumps(kwargs, sort_keys=True)
        
        # Create a unique hash
        hash_input = f"{prefix}:{args_str}:{kwargs_str}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        return f"{prefix}:{hash_value}"
    
    def cached(self, ttl_seconds: Optional[int] = None, prefix: Optional[str] = None):
        """
        Decorator for caching function results.
        
        Args:
            ttl_seconds: Optional TTL override in seconds
            prefix: Optional key prefix override (defaults to function name)
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                # Generate cache key
                key_prefix = prefix if prefix is not None else func.__name__
                cache_key = self.cache_key(key_prefix, *args, **kwargs)
                
                # Check cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl_seconds)
                
                return result
            return wrapper
        return decorator
    
    def cached_async(self, ttl_seconds: Optional[int] = None, prefix: Optional[str] = None):
        """
        Decorator for caching async function results.
        
        Args:
            ttl_seconds: Optional TTL override in seconds
            prefix: Optional key prefix override (defaults to function name)
            
        Returns:
            Decorated async function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                # Generate cache key
                key_prefix = prefix if prefix is not None else func.__name__
                cache_key = self.cache_key(key_prefix, *args, **kwargs)
                
                # Check cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Call function and cache result
                result = await func(*args, **kwargs)
                self.set(cache_key, result, ttl_seconds)
                
                return result
            return wrapper
        return decorator
    
    def _remove(self, key: str) -> None:
        """Internal method to remove a cache entry."""
        with self._get_lock(key):
            if key in self.cache:
                del self.cache[key]
    
    def _get_lock(self, key: str) -> RLock:
        """Get or create a lock for the given key."""
        with self.master_lock:
            if key not in self.locks:
                self.locks[key] = RLock()
            return self.locks[key]
    
    def cleanup(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        keys_to_remove = []
        
        # Find expired entries
        with self.master_lock:
            for key, entry in self.cache.items():
                if entry['expiry'] < now:
                    keys_to_remove.append(key)
        
        # Remove expired entries
        for key in keys_to_remove:
            self._remove(key)
            
        return len(keys_to_remove)


# Singleton cache instance
_cache_instance = None

def get_cache(ttl_seconds: int = 300) -> CacheService:
    """
    Get or create the global cache instance.
    
    Args:
        ttl_seconds: Default TTL for cache entries
        
    Returns:
        The global cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService(ttl_seconds)
    return _cache_instance