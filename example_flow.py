import asyncio
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
ORCH_DIR = ROOT_DIR.parent / "hala-ai-orchestrator"
if ORCH_DIR.exists():
    sys.path.insert(0, str(ORCH_DIR))

from hala_orchestrator import FlowRouter, SimplePlanner, StaticNewsTool, StaticPriceTool, setup_logging
from agents.orchestration import CryptoAgent, NewsAgent, WriterAgent


async def main() -> None:
    setup_logging()

    tools = [
        StaticNewsTool(),
        StaticPriceTool(),
    ]

    agents = [
        NewsAgent(tools=tools),
        CryptoAgent(tools=tools),
        WriterAgent(),
    ]

    router = FlowRouter(planner=SimplePlanner(), agents=agents)
    state = await router.run_mission("Give me a market briefing.")

    print("\n" + (state.final_output or "\n".join(state.findings)))


if __name__ == "__main__":
    asyncio.run(main())
