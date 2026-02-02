import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
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


def _next_run_time(hour: int, minute: int, tz_name: str) -> datetime:
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except Exception:
        tz = None

    now = datetime.now(tz=tz)
    run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_at <= now:
        run_at = run_at + timedelta(days=1)
    return run_at


async def run_once() -> None:
    await run_mission_from_config(mission_name="morning_newsletter")


def main() -> None:
    tz_name = os.getenv("NEWSLETTER_TZ", "America/New_York")
    hour = int(os.getenv("NEWSLETTER_HOUR", "6"))
    minute = int(os.getenv("NEWSLETTER_MINUTE", "5"))
    print(f"[scheduler] Starting. TZ={tz_name} time={hour:02d}:{minute:02d}")
    while True:
        next_run = _next_run_time(hour, minute, tz_name)
        sleep_seconds = max(0, int((next_run - datetime.now(tz=next_run.tzinfo)).total_seconds()))
        print(f"[scheduler] Next run at {next_run.isoformat()} (in {sleep_seconds}s)")
        time.sleep(sleep_seconds)
        print("[scheduler] Running morning newsletter...")
        try:
            asyncio.run(run_once())
        except Exception as exc:
            print(f"[scheduler] Error: {exc}")
        time.sleep(60)


if __name__ == "__main__":
    main()
