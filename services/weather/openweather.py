import os
from typing import Any, Dict, Optional

import httpx


OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = os.getenv("OPENWEATHER_BASE_URL", "https://api.openweathermap.org/data/2.5/weather")


async def fetch_current_weather(city: str, units: str = "metric") -> Dict[str, Any]:
    if not OPENWEATHER_API_KEY:
        raise RuntimeError("OPENWEATHER_API_KEY is not set.")

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": units,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPENWEATHER_BASE_URL, params=params)
        response.raise_for_status()
        payload = response.json()

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
