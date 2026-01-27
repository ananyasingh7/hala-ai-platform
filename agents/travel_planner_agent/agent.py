"""
Travel Planner Agent (Demo #1)
This is the first platform agent wired to the orchestrator SDK.
It relies on real APIs + the HalaAI engine (no mock data).
"""

import json
from typing import Any, Dict, Optional

from hala_orchestrator import Agent, MissionState, agent, get_logger


def _safe_json_extract(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


@agent(name="TravelPlannerAgent", description="Plans travel using weather + currency tools.")
class TravelPlannerAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        logger = get_logger(self.name, mission_id=state.mission_id, agent=self.name)

        hala = self.get_tool("hala_engine")
        weather = self.get_tool("openweather")
        fx = self.get_tool("exchange_rates")

        if not hala:
            raise RuntimeError("Hala engine tool is required for TravelPlannerAgent.")

        planner_prompt = (
            "Extract travel parameters as JSON. Use only fields you can infer.\n"
            "Fields: city, base_currency, target_currency, amount\n"
            "User request:\n"
            f"{state.objective}\n"
            "Return JSON only."
        )

        extraction = await hala.run(
            prompt=planner_prompt,
            session_id=state.mission_id,
            start_session=True,
            include_history=False,
            max_tokens=self.runtime.max_tokens if self.runtime else None,
        )

        parsed = _safe_json_extract(extraction)
        city = parsed.get("city")
        base_currency = parsed.get("base_currency") or "USD"
        target_currency = parsed.get("target_currency")
        amount = parsed.get("amount")

        if not city:
            raise ValueError("TravelPlannerAgent requires a city to continue.")

        weather_data: Optional[Dict[str, Any]] = None
        if weather:
            try:
                weather_data = await weather.run(city=city)
            except Exception as exc:
                logger.warning("Weather tool failed: %s", exc)

        fx_data: Optional[Dict[str, Any]] = None
        if fx and target_currency:
            try:
                fx_data = await fx.run(
                    base=base_currency,
                    target=target_currency,
                    amount=amount,
                )
            except Exception as exc:
                logger.warning("FX tool failed: %s", exc)

        state.data["travel"] = {
            "city": city,
            "base_currency": base_currency,
            "target_currency": target_currency,
            "amount": amount,
            "weather": weather_data,
            "fx": fx_data,
        }

        summary_prompt = (
            "You are a travel planner. Use the data below to create a concise travel brief.\n"
            "Include weather summary and currency conversion if available.\n"
            f"Data: {state.data['travel']}"
        )

        response = await hala.run(
            prompt=summary_prompt,
            session_id=state.mission_id,
            start_session=False,
            include_history=False,
            max_tokens=self.runtime.max_tokens if self.runtime else None,
        )

        state.final_output = response
        return state
