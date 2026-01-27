import asyncio
from typing import Any, Dict

from hala_orchestrator.tools import Tool
from services.hala_ws import query_hala
from tools.exchange.tool import ExchangeRatesTool
from tools.weather.tool import OpenWeatherTool


class HalaWSTool(Tool):
    def __init__(self, ws_url: str, timeout_sec: float = 6.0, max_tokens: int = 256):
        self.name = "hala_engine"
        self.ws_url = ws_url
        self.timeout_sec = timeout_sec
        self.max_tokens = max_tokens

    async def run(self, **kwargs: Any) -> str:
        prompt = kwargs.get("prompt", "")
        session_id = kwargs.get("session_id")
        system_prompt = kwargs.get("system_prompt")
        include_history = kwargs.get("include_history", False)
        start_session = kwargs.get("start_session", False)
        max_tokens = kwargs.get("max_tokens")
        if not max_tokens:
            max_tokens = self.max_tokens

        return await asyncio.wait_for(
            query_hala(
                prompt,
                session_id=session_id,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                start_session=start_session,
                include_history=include_history,
                ws_url=self.ws_url,
            ),
            timeout=self.timeout_sec,
        )


def get_tool_factories() -> Dict[str, callable]:
    def hala_factory(name: str, config: Dict[str, Any]) -> Tool:
        return HalaWSTool(
            ws_url=config.get("ws_url", "ws://localhost:8000/ws/chat/v2"),
            timeout_sec=float(config.get("timeout_sec", 6)),
            max_tokens=int(config.get("max_tokens", 256)),
        )

    def openweather_factory(name: str, config: Dict[str, Any]) -> Tool:
        units = config.get("units", "metric")
        tool = OpenWeatherTool(units=units)
        tool.name = name
        return tool

    def exchange_factory(name: str, config: Dict[str, Any]) -> Tool:
        tool = ExchangeRatesTool()
        tool.name = name
        return tool

    return {
        "hala_ws": hala_factory,
        "openweather": openweather_factory,
        "exchange_rates": exchange_factory,
    }
