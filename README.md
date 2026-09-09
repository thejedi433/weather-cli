# weather-cli

Minimal weather CLI with location memory and daily forecast caching.

Uses the free [wttr.in](https://wttr.in) API — no API key required.

## Features

- **Current conditions** — temperature, feels-like, humidity, wind, description
- **3-day forecast** — daily high/low/avg with hourly breakdown and rain chance
- **Location memory** — set a default location, query without typing it each time
- **Forecast caching** — 1-hour TTL, avoids redundant API calls
- **JSON output** — machine-readable with `--json`
- **No dependencies beyond click + requests**

## Installation

```bash
git clone https://github.com/thejedi433/weather-cli.git
cd weather-cli
uv sync
```

## Usage

```bash
# Current weather (with default location set)
weather set-location Oslo
weather current

# Current weather for a specific location
weather current "New York"

# JSON output
weather current London --json

# 3-day forecast
weather forecast

# Forecast for a specific location
weather forecast Tokyo

# Clear the cache
weather clear-cache
```

## Development

```bash
uv sync --frozen
uv run pytest --cov=weather_cli --cov-report=term-missing
```

Coverage requirement: 100%.
