import os
from typing import Any, Dict, Optional

import httpx


OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = os.getenv("OPENWEATHER_BASE_URL", "https://api.openweathermap.org/data/2.5/weather")


def _normalize_city(city: str) -> str:
    cleaned = city.strip()
    if not cleaned:
        return cleaned
    return cleaned


def _append_us_if_state_only(city: str) -> str:
    parts = [part.strip() for part in city.split(",")]
    if len(parts) == 2 and len(parts[1]) == 2 and parts[1].isalpha():
        return f"{parts[0]}, {parts[1]}, US"
    return city


async def _fetch_weather(city: str, units: str) -> Dict[str, Any]:
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": units,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPENWEATHER_BASE_URL, params=params)
        response.raise_for_status()
        return response.json()


async def fetch_current_weather(city: str, units: str = "metric") -> Dict[str, Any]:
    if not OPENWEATHER_API_KEY:
        raise RuntimeError("OPENWEATHER_API_KEY is not set.")

    city = _normalize_city(city)
    try:
        payload = await _fetch_weather(city, units)
    except httpx.HTTPStatusError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            fallback_city = _append_us_if_state_only(city)
            if fallback_city != city:
                payload = await _fetch_weather(fallback_city, units)
            else:
                raise
        else:
            raise

    weather = payload.get("weather", [{}])[0]
    main = payload.get("main", {})
    wind = payload.get("wind", {})
    sys = payload.get("sys", {})

    return {
        "city": payload.get("name", city),
        "country": sys.get("country"),
        "description": weather.get("description"),
        "temperature": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "wind_speed": wind.get("speed"),
        "units": units,
    }
