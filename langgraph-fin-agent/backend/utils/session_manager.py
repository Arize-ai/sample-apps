import hashlib
import json
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages cached sessions for different environment configurations."""
    
    def __init__(self, cache_ttl_minutes: int = 30):
        self._cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._cache_ttl = timedelta(minutes=cache_ttl_minutes)
        
    def _generate_cache_key(self, env_vars: Optional[Dict[str, str]]) -> str:
        """Generate a unique cache key for the environment configuration."""
        if not env_vars:
            return "default"
        
        # Sort the dictionary to ensure consistent hashing
        sorted_env = dict(sorted(env_vars.items()))
        env_string = json.dumps(sorted_env, sort_keys=True)
        
        # Create a hash of the environment configuration
        return hashlib.sha256(env_string.encode()).hexdigest()[:16]
    
    def get_cached_components(self, env_vars: Optional[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Retrieve cached components for the given environment configuration."""
        cache_key = self._generate_cache_key(env_vars)
        
        if cache_key in self._cache:
            components, timestamp = self._cache[cache_key]
            
            # Check if cache is still valid
            if datetime.now() - timestamp < self._cache_ttl:
                logger.info(f"Using cached components for key: {cache_key}")
                return components
            else:
                # Cache expired, remove it
                logger.info(f"Cache expired for key: {cache_key}")
                del self._cache[cache_key]
        
        return None
    
    def cache_components(self, env_vars: Optional[Dict[str, str]], components: Dict[str, Any]):
        """Cache components for the given environment configuration."""
        cache_key = self._generate_cache_key(env_vars)
        self._cache[cache_key] = (components, datetime.now())
        logger.info(f"Cached components for key: {cache_key}")
        
        # Clean up old entries
        self._cleanup_expired_cache()
    
    def _cleanup_expired_cache(self):
        """Remove expired cache entries."""
        current_time = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
            logger.info(f"Removed expired cache entry: {key}")
    
    def clear_cache(self):
        """Clear all cached sessions."""
        self._cache.clear()
        logger.info("Cleared all cached sessions") 