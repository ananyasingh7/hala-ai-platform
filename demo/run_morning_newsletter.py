import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
ORCH_DIR = ROOT_DIR.parent / "hala-ai-orchestrator"
if ORCH_DIR.exists():
    sys.path.insert(0, str(ORCH_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(dotenv_path=ROOT_DIR / ".env")
os.environ.setdefault("HALA_WS_URL", "ws://localhost:8000/ws/chat/v2")

from orchestration.runner import run_mission_from_config
from services.newsletter.config import load_newsletter_config


async def main() -> None:
    state = await run_mission_from_config(mission_name="morning_newsletter")
    config = load_newsletter_config()
    output_dir = config.get("delivery", {}).get("output_dir", "demo/reports/morning_newsletter")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    today = state.data.get("newsletter", {}).get("generated_at")
    if not today:
        today = "latest"
    else:
        today = today.split("T", 1)[0]

    json_path = Path(output_dir) / f"morning_newsletter_state_{today}.json"
    payload = {
        "mission_id": state.mission_id,
        "objective": state.objective,
        "final_output": state.final_output,
        "data": state.data,
        "errors": state.errors,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    delivery = state.data.get("delivery") or {}
    output_md = delivery.get("output_path")
    if output_md:
        print(f"Markdown written to: {output_md}")
    print(f"JSON written to: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
