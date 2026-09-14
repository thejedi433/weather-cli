"""CLI interface for weather-cli."""
import json
from pathlib import Path
from typing import Optional

import click

from weather_cli import __version__
from weather_cli.cache import WeatherCache, DEFAULT_CACHE_TTL
from weather_cli.client import (
    get_current,
    get_forecast,
    WeatherError,
)


def get_cache() -> WeatherCache:
    """Get the default cache instance."""
    cache_dir = Path.home() / ".cache" / "weather-cli"
    return WeatherCache(cache_dir)


@click.group()
@click.version_option(version=__version__, prog_name="weather-cli")
def main():
    """Minimal weather CLI with location memory and forecast caching."""
    pass


@main.command()
@click.argument("location", required=False)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--max-age", default=DEFAULT_CACHE_TTL, help="Cache max age in seconds")
def current(location: Optional[str], json_output: bool, max_age: int):
    """Get current weather conditions."""
    cache = get_cache()
    
    if location is None:
        location = cache.get_default_location()
        if location is None:
            click.echo("Error: no location provided and no default set", err=True)
            click.echo("Use: weather set-location <city>", err=True)
            raise SystemExit(1)
    
    try:
        data = get_current(location, cache=cache, max_age=max_age)
    except WeatherError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    
    if json_output:
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Weather in {data['location']}, {data['country']}:")
        click.echo(f"  {data['description']}")
        click.echo(f"  Temperature: {data['temp_c']}°C (feels like {data['feels_like_c']}°C)")
        click.echo(f"  Humidity: {data['humidity']}%")
        click.echo(f"  Wind: {data['wind_kmph']} km/h {data['wind_dir']}")


@main.command()
@click.argument("location", required=False)
@click.option("--max-age", default=DEFAULT_CACHE_TTL, help="Cache max age in seconds")
def forecast(location: Optional[str], max_age: int):
    """Get 3-day forecast."""
    cache = get_cache()

    if location is None:
        location = cache.get_default_location()
        if location is None:
            click.echo("Error: no location provided and no default set", err=True)
            click.echo("Use: weather set-location <city>", err=True)
            raise SystemExit(1)

    try:
        days = get_forecast(location, cache=cache, max_age=max_age)
    except WeatherError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    
    for day in days:
        click.echo(f"\n{day['date']}:")
        click.echo(f"  High: {day['max_c']}°C  Low: {day['min_c']}°C  Avg: {day['avg_c']}°C")
        click.echo("  Hourly:")
        for hour in day["hourly"]:
            time_str = f"{int(hour['time'])//100:02d}:00"
            click.echo(
                f"    {time_str} - {hour['temp_c']}°C, "
                f"{hour['description']}, "
                f"rain {hour['rain_chance']}%"
            )


@main.command("set-location")
@click.argument("location")
def set_location(location: str):
    """Set default location for weather queries."""
    cache = get_cache()
    cache.set_default_location(location)
    click.echo(f"Default location set to: {location}")


@main.command("clear-cache")
def clear_cache():
    """Clear all cached weather data."""
    cache = get_cache()
    cache.clear()
    click.echo("Cache cleared")

