from typing import Any, Dict

from hala_orchestrator.tools import Tool
from services.weather.openweather import fetch_current_weather


class OpenWeatherTool(Tool):
    name = "openweather"

    def __init__(self, units: str = "metric"):
        self.units = units

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        city = kwargs.get("city")
        if not city:
            raise ValueError("OpenWeatherTool requires a city.")
        units = kwargs.get("units") or self.units
        return await fetch_current_weather(city=city, units=units)
