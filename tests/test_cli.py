"""Tests for weather_cli CLI module."""
import json
import pytest
import requests
import responses
from click.testing import CliRunner

from weather_cli.cli import main
from weather_cli.cache import WeatherCache


@pytest.fixture
def runner():
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture
def tmp_cache(tmp_path):
    """Return a WeatherCache using a temp directory."""
    return WeatherCache(cache_dir=str(tmp_path))


SAMPLE_RESPONSE = {
    "current_condition": [{
        "temp_C": "15",
        "FeelsLikeC": "14",
        "humidity": "72",
        "weatherDesc": [{"value": "Partly cloudy"}],
        "windspeedKmph": "12",
        "winddir16Point": "SW",
    }],
    "nearest_area": [{
        "areaName": [{"value": "Oslo"}],
        "country": [{"value": "Norway"}],
        "region": [{"value": "Oslo"}],
    }],
    "weather": [
        {
            "date": "2026-09-09",
            "maxtempC": "18",
            "mintempC": "9",
            "avgtempC": "13",
            "hourly": [
                {"time": "0", "tempC": "10", "chanceofrain": "20",
                 "weatherDesc": [{"value": "Cloudy"}]},
                {"time": "600", "tempC": "11", "chanceofrain": "30",
                 "weatherDesc": [{"value": "Light rain"}]},
                {"time": "1200", "tempC": "17", "chanceofrain": "10",
                 "weatherDesc": [{"value": "Sunny"}]},
                {"time": "1800", "tempC": "14", "chanceofrain": "15",
                 "weatherDesc": [{"value": "Partly cloudy"}]},
            ],
        },
    ],
}


class TestCLI:
    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "weather-cli" in result.output

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "weather" in result.output
        assert "forecast" in result.output
        assert "set-location" in result.output

    @responses.activate
    def test_current_command_with_location(self, runner, tmp_cache, monkeypatch):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        result = runner.invoke(main, ["current", "Oslo"])
        assert result.exit_code == 0
        assert "Oslo" in result.output
        assert "15" in result.output  # temp
        assert "Partly cloudy" in result.output

    @responses.activate
    def test_forecast_command(self, runner, tmp_cache, monkeypatch):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        result = runner.invoke(main, ["forecast", "Oslo"])
        assert result.exit_code == 0
        assert "2026-09-09" in result.output
        assert "18" in result.output  # max temp
        assert "09" in result.output  # min temp

    def test_set_location_command(self, runner, tmp_cache, monkeypatch):
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        result = runner.invoke(main, ["set-location", "Oslo"])
        assert result.exit_code == 0
        assert "Oslo" in result.output
        assert tmp_cache.get_default_location() == "Oslo"

    @responses.activate
    def test_current_uses_default_location(self, runner, tmp_cache, monkeypatch):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        tmp_cache.set_default_location("Oslo")
        result = runner.invoke(main, ["current"])
        assert result.exit_code == 0
        assert "Oslo" in result.output

    def test_current_fails_without_location_or_default(self, runner, tmp_cache, monkeypatch):
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        result = runner.invoke(main, ["current"])
        assert result.exit_code != 0
        assert "location" in result.output.lower() or "error" in result.output.lower()

    @responses.activate
    def test_json_output(self, runner, tmp_cache, monkeypatch):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        result = runner.invoke(main, ["current", "Oslo", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["location"] == "Oslo"
        assert data["temp_c"] == 15

    def test_clear_cache_command(self, runner, tmp_cache, monkeypatch):
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        tmp_cache.set("test", {"value": 1})
        result = runner.invoke(main, ["clear-cache"])
        assert result.exit_code == 0
        assert "cleared" in result.output.lower()
        assert tmp_cache.get("test") is None

    @responses.activate
    def test_current_handles_weather_error(self, runner, tmp_cache, monkeypatch):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            body=requests.exceptions.ConnectionError("network down"),
        )
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        result = runner.invoke(main, ["current", "Oslo"])
        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output

    @responses.activate
    def test_forecast_handles_weather_error(self, runner, tmp_cache, monkeypatch):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json={"error": "not found"},
            status=404,
        )
        monkeypatch.setattr("weather_cli.cli.get_cache", lambda: tmp_cache)
        result = runner.invoke(main, ["forecast", "Oslo"])
        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output

    def test_get_cache_creates_cache_instance(self):
        """Test that get_cache returns a WeatherCache instance."""
        from weather_cli.cli import get_cache
        cache = get_cache()
        assert isinstance(cache, WeatherCache)
