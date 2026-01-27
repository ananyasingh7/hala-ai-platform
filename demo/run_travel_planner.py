import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Demo script for the TravelPlannerAgent.
# Requires HalaAI engine running + HALA_WS_URL set.
# Optional: OPENWEATHER_API_KEY for OpenWeather.

ROOT_DIR = Path(__file__).resolve().parents[1]
ORCH_DIR = ROOT_DIR.parent / "hala-ai-orchestrator"
if ORCH_DIR.exists():
    sys.path.insert(0, str(ORCH_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(dotenv_path=ROOT_DIR / ".env")
os.environ.setdefault("HALA_WS_URL", "ws://localhost:8000/ws/chat/v2")

from orchestration.runner import run_mission_from_config


async def main() -> None:
    state = await run_mission_from_config(
        mission_name="travel_planner",
        objective_override="Plan a 4-day trip to Tokyo. Convert 1500 USD to JPY.",
    )
    print(state.final_output or state.data)


if __name__ == "__main__":
    asyncio.run(main())
