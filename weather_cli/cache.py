"""Cache module for weather data with TTL support."""
import json
import time
from pathlib import Path
from typing import Any, Optional


DEFAULT_CACHE_TTL = 3600  # 1 hour


class WeatherCache:
    """Simple JSON-based cache with TTL and location memory."""

    def __init__(self, cache_dir: str | Path):
        """Initialize cache with given directory.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_key(self, key: str) -> str:
        """Normalize cache key (lowercase, strip whitespace)."""
        return key.strip().lower()

    def get(self, key: str, max_age: Optional[int] = None) -> Optional[Any]:
        """Get cached value if it exists and hasn't expired.
        
        Args:
            key: Cache key
            max_age: Maximum age in seconds (uses default TTL if None)
            
        Returns:
            Cached value or None if missing/expired
        """
        key = self._normalize_key(key)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            data = json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        
        if max_age is not None:
            age = time.time() - data.get("timestamp", 0)
            if age > max_age:
                return None
        
        return data.get("value")

    def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> None:
        """Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        key = self._normalize_key(key)
        cache_file = self.cache_dir / f"{key}.json"
        data = {
            "value": value,
            "timestamp": time.time(),
        }
        cache_file.write_text(json.dumps(data, indent=2))

    def get_default_location(self) -> Optional[str]:
        """Get the default location for weather queries.
        
        Returns:
            Default location or None if not set
        """
        return self.get("default_location")

    def set_default_location(self, location: str) -> None:
        """Set the default location for weather queries.
        
        Args:
            location: Location name
        """
        self.set("default_location", location)

    def clear(self) -> None:
        """Clear all cached data."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
