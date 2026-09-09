"""Tests for weather_cli client module."""
import json
import time
import pytest
import requests
import responses

from weather_cli import client
from weather_cli.cache import WeatherCache


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
        {
            "date": "2026-09-10",
            "maxtempC": "16",
            "mintempC": "8",
            "avgtempC": "12",
            "hourly": [
                {"time": "0", "tempC": "9", "chanceofrain": "40",
                 "weatherDesc": [{"value": "Rain"}]},
                {"time": "600", "tempC": "10", "chanceofrain": "50",
                 "weatherDesc": [{"value": "Rain"}]},
                {"time": "1200", "tempC": "14", "chanceofrain": "20",
                 "weatherDesc": [{"value": "Cloudy"}]},
                {"time": "1800", "tempC": "12", "chanceofrain": "30",
                 "weatherDesc": [{"value": "Cloudy"}]},
            ],
        },
        {
            "date": "2026-09-11",
            "maxtempC": "20",
            "mintempC": "10",
            "avgtempC": "15",
            "hourly": [
                {"time": "0", "tempC": "11", "chanceofrain": "5",
                 "weatherDesc": [{"value": "Clear"}]},
                {"time": "600", "tempC": "12", "chanceofrain": "10",
                 "weatherDesc": [{"value": "Clear"}]},
                {"time": "1200", "tempC": "19", "chanceofrain": "0",
                 "weatherDesc": [{"value": "Sunny"}]},
                {"time": "1800", "tempC": "16", "chanceofrain": "5",
                 "weatherDesc": [{"value": "Clear"}]},
            ],
        },
    ],
}


class TestGetCurrent:
    @responses.activate
    def test_fetches_and_parses_current_conditions(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        result = client.get_current("Oslo", cache=tmp_cache)
        assert result["location"] == "Oslo"
        assert result["country"] == "Norway"
        assert result["temp_c"] == 15
        assert result["feels_like_c"] == 14
        assert result["humidity"] == 72
        assert result["description"] == "Partly cloudy"
        assert result["wind_kmph"] == 12
        assert result["wind_dir"] == "SW"

    @responses.activate
    def test_uses_cache_on_second_call(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        client.get_current("Oslo", cache=tmp_cache, max_age=600)
        client.get_current("Oslo", cache=tmp_cache, max_age=600)
        # Only one HTTP call made
        assert len(responses.calls) == 1

    @responses.activate
    def test_raises_on_network_error(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            body=requests.exceptions.ConnectionError("no network"),
        )
        with pytest.raises(client.WeatherError, match="network"):
            client.get_current("Oslo", cache=tmp_cache)

    @responses.activate
    def test_raises_on_invalid_json(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            body="not json",
            status=200,
        )
        with pytest.raises(client.WeatherError, match="parse"):
            client.get_current("Oslo", cache=tmp_cache)

    @responses.activate
    def test_raises_on_404(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json={"error": "not found"},
            status=404,
        )
        with pytest.raises(client.WeatherError, match="404"):
            client.get_current("Oslo", cache=tmp_cache)

    @responses.activate
    def test_raises_on_500_error(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json={"error": "server error"},
            status=500,
        )
        with pytest.raises(client.WeatherError, match="500"):
            client.get_current("Oslo", cache=tmp_cache)

    @responses.activate
    def test_works_without_cache(self):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        result = client.get_current("Oslo", cache=None)
        assert result["location"] == "Oslo"
        assert result["temp_c"] == 15

    @responses.activate
    def test_forecast_works_without_cache(self):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        days = client.get_forecast("Oslo", cache=None)
        assert len(days) == 3

    def test_get_forecast_raises_when_no_cache_and_no_location(self):
        with pytest.raises(client.WeatherError, match="location"):
            client.get_forecast(None, cache=None)


class TestGetForecast:
    @responses.activate
    def test_returns_three_day_forecast(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        days = client.get_forecast("Oslo", cache=tmp_cache)
        assert len(days) == 3
        assert days[0]["date"] == "2026-09-09"
        assert days[0]["max_c"] == 18
        assert days[0]["min_c"] == 9
        assert days[0]["avg_c"] == 13
        assert len(days[0]["hourly"]) == 4
        assert days[0]["hourly"][2]["temp_c"] == 17

    @responses.activate
    def test_default_location_used(self, tmp_cache):
        """When no location is passed, it falls back to cache default."""
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        # Pre-set default in cache
        tmp_cache.set_default_location("Oslo")
        days = client.get_forecast(None, cache=tmp_cache)
        assert len(days) == 3
        # URL called was /Oslo
        assert "Oslo" in responses.calls[0].request.url

    def test_raises_when_no_location_and_no_default(self, tmp_cache):
        with pytest.raises(client.WeatherError, match="location"):
            client.get_forecast(None, cache=tmp_cache)

    @responses.activate
    def test_cache_shared_between_current_and_forecast(self, tmp_cache):
        responses.add(
            responses.GET,
            "https://wttr.in/Oslo",
            json=SAMPLE_RESPONSE,
            status=200,
        )
        client.get_current("Oslo", cache=tmp_cache, max_age=600)
        client.get_forecast("Oslo", cache=tmp_cache, max_age=600)
        # One HTTP call serves both (same response has both)
        assert len(responses.calls) == 1


class TestParseResponse:
    def test_parse_current_extracts_all_fields(self):
        result = client._parse_current(SAMPLE_RESPONSE)
        assert result["location"] == "Oslo"
        assert result["country"] == "Norway"
        assert result["region"] == "Oslo"
        assert result["temp_c"] == 15
        assert result["feels_like_c"] == 14
        assert result["humidity"] == 72
        assert result["description"] == "Partly cloudy"
        assert result["wind_kmph"] == 12
        assert result["wind_dir"] == "SW"

    def test_parse_forecast_extracts_days(self):
        days = client._parse_forecast(SAMPLE_RESPONSE)
        assert len(days) == 3
        assert days[0]["date"] == "2026-09-09"
        assert days[0]["max_c"] == 18
        assert days[0]["min_c"] == 9
        hourly = days[0]["hourly"]
        assert len(hourly) == 4
        assert hourly[0]["time"] == "0"
        assert hourly[0]["temp_c"] == 10
        assert hourly[0]["rain_chance"] == 20
        assert hourly[0]["description"] == "Cloudy"
