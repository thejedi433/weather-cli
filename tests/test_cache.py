"""Tests for weather_cli cache module."""
import json
import time
import pytest

from weather_cli.cache import WeatherCache, DEFAULT_CACHE_TTL


@pytest.fixture
def cache(tmp_path):
    """Return a WeatherCache using a temp directory."""
    return WeatherCache(cache_dir=str(tmp_path))


class TestWeatherCache:
    def test_create_cache_dir(self, tmp_path):
        cache_dir = str(tmp_path / "new_cache")
        cache = WeatherCache(cache_dir=cache_dir)
        assert (tmp_path / "new_cache").is_dir()

    def test_get_returns_none_when_empty(self, cache):
        assert cache.get("missing_key") is None

    def test_set_and_get(self, cache):
        data = {"temp": 15, "city": "Oslo"}
        cache.set("oslo", data, ttl=60)
        result = cache.get("oslo")
        assert result == data

    def test_get_returns_none_after_ttl(self, cache):
        cache.set("oslo", {"temp": 15}, ttl=0)
        # TTL=0 means it should expire immediately - but we need time to pass
        # Use a negative TTL test by manipulating the stored timestamp
        result = cache.get("oslo", max_age=0)
        # With max_age=0, anything older than 0 seconds is expired
        assert result is None

    def test_set_default_location(self, cache):
        cache.set_default_location("Oslo")
        assert cache.get_default_location() == "Oslo"

    def test_get_default_location_returns_none_when_not_set(self, cache):
        assert cache.get_default_location() is None

    def test_clear_removes_all_entries(self, cache):
        cache.set("key1", {"a": 1})
        cache.set("key2", {"b": 2})
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_file_is_json(self, cache):
        cache.set("test", {"value": 42})
        cache_file = cache.cache_dir / "test.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert data["value"] == {"value": 42}
        assert "timestamp" in data

    def test_invalid_json_file_returns_none(self, cache):
        cache_file = cache.cache_dir / "bad.json"
        cache_file.write_text("not valid json")
        result = cache.get("bad")
        assert result is None

    def test_location_key_normalization(self, cache):
        """Location keys should be normalized (lowercase, stripped)."""
        cache.set("Oslo", {"temp": 15})
        # Should retrieve with different case
        result = cache.get("oslo")
        assert result == {"temp": 15}


class TestCacheTTL:
    def test_fresh_entry_returned(self, cache):
        cache.set("oslo", {"temp": 15}, ttl=3600)
        result = cache.get("oslo", max_age=3600)
        assert result == {"temp": 15}

    def test_expired_entry_returns_none(self, cache):
        # Manually write an old entry
        cache_file = cache.cache_dir / "old.json"
        old_data = {"value": 1, "timestamp": time.time() - 7200}
        cache_file.write_text(json.dumps(old_data))
        # Request with 1 hour max age - entry is 2 hours old
        result = cache.get("old", max_age=3600)
        assert result is None

    def test_default_ttl_used_when_not_specified(self, cache):
        cache.set("oslo", {"temp": 15})
        # Should use DEFAULT_CACHE_TTL
        result = cache.get("oslo")
        assert result == {"temp": 15}
