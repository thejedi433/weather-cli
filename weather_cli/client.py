"""Client module for fetching weather data from wttr.in."""
import json
from typing import Any, Dict, List, Optional
import requests

from weather_cli.cache import WeatherCache, DEFAULT_CACHE_TTL


API_URL = "https://wttr.in"


class WeatherError(Exception):
    """Exception raised for weather-related errors."""
    pass


def get_current(
    location: str,
    cache: Optional[WeatherCache] = None,
    max_age: int = DEFAULT_CACHE_TTL,
) -> Dict[str, Any]:
    """Get current weather conditions for a location.
    
    Args:
        location: City name or coordinates
        cache: WeatherCache instance (optional)
        max_age: Maximum cache age in seconds
        
    Returns:
        Dict with current weather data
        
    Raises:
        WeatherError: If fetch or parse fails
    """
    data = _fetch_weather_data(location, cache, max_age)
    return _parse_current(data)


def get_forecast(
    location: Optional[str],
    cache: Optional[WeatherCache] = None,
    max_age: int = DEFAULT_CACHE_TTL,
) -> List[Dict[str, Any]]:
    """Get 3-day forecast for a location.
    
    Args:
        location: City name or coordinates (None uses default)
        cache: WeatherCache instance (optional)
        max_age: Maximum cache age in seconds
        
    Returns:
        List of 3 daily forecast dicts
        
    Raises:
        WeatherError: If location is missing or fetch fails
    """
    if location is None:
        if cache is None:
            raise WeatherError("location required: no location provided and no default set")
        location = cache.get_default_location()
        if location is None:
            raise WeatherError("location required: no location provided and no default set")
    
    data = _fetch_weather_data(location, cache, max_age)
    return _parse_forecast(data)


def _fetch_weather_data(
    location: str,
    cache: Optional[WeatherCache],
    max_age: int,
) -> Dict[str, Any]:
    """Fetch weather data from API or cache.
    
    Args:
        location: Location name
        cache: WeatherCache instance
        max_age: Maximum cache age
        
    Returns:
        Raw weather data dict
        
    Raises:
        WeatherError: If fetch or parse fails
    """
    cache_key = f"weather_{location}"
    
    # Try cache first
    if cache is not None:
        cached = cache.get(cache_key, max_age=max_age)
        if cached is not None:
            return cached
    
    # Fetch from API
    try:
        response = requests.get(f"{API_URL}/{location}", timeout=10)
    except requests.RequestException as e:
        raise WeatherError(f"network error: {e}") from e
    
    if response.status_code == 404:
        raise WeatherError(f"location not found: 404")
    
    if response.status_code != 200:
        raise WeatherError(f"API error: {response.status_code}")
    
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        raise WeatherError(f"parse error: invalid JSON response") from e
    
    # Cache the result
    if cache is not None:
        cache.set(cache_key, data)
    
    return data


def _parse_current(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse current weather conditions from API response.
    
    Args:
        data: Raw API response
        
    Returns:
        Dict with parsed current weather data
    """
    current = data["current_condition"][0]
    area = data["nearest_area"][0]
    
    return {
        "location": area["areaName"][0]["value"],
        "country": area["country"][0]["value"],
        "region": area["region"][0]["value"],
        "temp_c": int(current["temp_C"]),
        "feels_like_c": int(current["FeelsLikeC"]),
        "humidity": int(current["humidity"]),
        "description": current["weatherDesc"][0]["value"],
        "wind_kmph": int(current["windspeedKmph"]),
        "wind_dir": current["winddir16Point"],
    }


def _parse_forecast(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse 3-day forecast from API response.
    
    Args:
        data: Raw API response
        
    Returns:
        List of 3 daily forecast dicts
    """
    days = []
    for day_data in data["weather"]:
        day = {
            "date": day_data["date"],
            "max_c": int(day_data["maxtempC"]),
            "min_c": int(day_data["mintempC"]),
            "avg_c": int(day_data["avgtempC"]),
            "hourly": [],
        }
        
        for hour_data in day_data["hourly"]:
            hour = {
                "time": hour_data["time"],
                "temp_c": int(hour_data["tempC"]),
                "rain_chance": int(hour_data["chanceofrain"]),
                "description": hour_data["weatherDesc"][0]["value"],
            }
            day["hourly"].append(hour)
        
        days.append(day)
    
    return days
