import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from config.logging import get_logger
from services.hala_ws import query_hala
from services.whoop_client import WhoopClient, get_access_token_for_user
from services.whoop_coach import build_context_snapshot, summarize_whoop_data
from services.whoop_store import get_any_user_token

logger = get_logger("WhoopBriefing")

BRIEFING_SYSTEM_PROMPT = (
    "You are HalaAI, an active coach."
    " Provide a concise daily briefing based on WHOOP data."
    " Use 2-4 sentences. Mention recovery, sleep, and strain implications."
    " If a metric is missing, acknowledge it briefly."
)


def _get_env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def _safe_number(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_percent(value: Optional[float]) -> str:
    num = _safe_number(value)
    if num is None:
        return "N/A"
    return f"{num:.0f}%"


def _format_value(value: Optional[float], suffix: str = "") -> str:
    num = _safe_number(value)
    if num is None:
        return "N/A"
    if suffix:
        return f"{num:.1f}{suffix}"
    return f"{num:.1f}"


def _format_duration_millis(value: Optional[float]) -> str:
    num = _safe_number(value)
    if num is None:
        return "N/A"
    seconds = num / 1000.0 if num > 10000 else num
    hours = seconds / 3600.0
    return f"{hours:.2f}h"


def _get_summary_date(summary: Dict) -> str:
    for key in ("sleep", "cycle"):
        entry = summary.get(key) or {}
        for field in ("end", "start"):
            value = entry.get(field)
            if value:
                return value
    return datetime.now(timezone.utc).isoformat()


def _get_auth_url() -> str:
    base_url = os.getenv("WHOOP_PUBLIC_BASE_URL")
    if base_url:
        return f"{base_url.rstrip('/')}/whoop/auth"

    redirect_uri = os.getenv("WHOOP_REDIRECT_URI")
    if redirect_uri and redirect_uri.endswith("/whoop/callback"):
        return redirect_uri.replace("/whoop/callback", "/whoop/auth")

    return "http://localhost:8765/whoop/auth"


def build_briefing_payload(summary: Dict, thoughts: str) -> Dict:
    recovery = summary.get("recovery", {}).get("score", {})
    sleep = summary.get("sleep", {}).get("score", {})
    sleep_stage = sleep.get("stage_summary", {}) if isinstance(sleep, dict) else {}
    cycle = summary.get("cycle", {}).get("score", {})
    workout = summary.get("workout", {})

    date = _get_summary_date(summary)

    return {
        "title": "WHOOP Daily Briefing",
        "date": date,
        "recovery": (
            f"{_format_percent(recovery.get('recovery_score'))} | "
            f"HRV {_format_value(recovery.get('hrv_rmssd_milli'), 'ms')} | "
            f"RHR {_format_value(recovery.get('resting_heart_rate'), 'bpm')}"
        ),
        "sleep": (
            f"Perf {_format_percent(sleep.get('sleep_performance_percentage'))} | "
            f"Eff {_format_percent(sleep.get('sleep_efficiency_percentage'))} | "
            f"Dur {_format_duration_millis(sleep_stage.get('total_sleep_time_milli') or sleep_stage.get('total_in_bed_time_milli'))}"
        ),
        "strain": (
            f"{cycle.get('strain') if cycle.get('strain') is not None else 'N/A'} | "
            f"Avg HR {_format_value(cycle.get('average_heart_rate'), 'bpm')}"
        ),
        "workout": (
            f"{workout.get('sport_name') or 'N/A'} | "
            f"Strain {workout.get('score', {}).get('strain') if isinstance(workout.get('score'), dict) else 'N/A'}"
        ),
        "thoughts": thoughts.strip() if thoughts else "No coach notes yet.",
    }


def build_discord_embed_dict(payload: Dict) -> Dict:
    return {
        "title": payload.get("title"),
        "description": f"Date: {payload.get('date')}",
        "color": 0x2ECC71,
        "fields": [
            {"name": "Recovery", "value": payload.get("recovery"), "inline": True},
            {"name": "Sleep", "value": payload.get("sleep"), "inline": True},
            {"name": "Strain", "value": payload.get("strain"), "inline": True},
            {"name": "Workout", "value": payload.get("workout"), "inline": True},
            {"name": "Coach Thoughts", "value": payload.get("thoughts"), "inline": False},
        ],
        "footer": {"text": "HalaAI Active Coach"},
    }


def build_briefing_text(payload: Dict) -> str:
    lines = [
        payload.get("title", "WHOOP Daily Briefing"),
        f"Date: {payload.get('date')}",
        f"Recovery: {payload.get('recovery')}",
        f"Sleep: {payload.get('sleep')}",
        f"Strain: {payload.get('strain')}",
        f"Workout: {payload.get('workout')}",
        "Coach Thoughts:",
        payload.get("thoughts", "No coach notes yet."),
    ]

    return "\n".join(lines)


async def _fetch_latest_summary(user_id: str) -> Dict:
    client_id = _get_env("WHOOP_CLIENT_ID")
    client_secret = _get_env("WHOOP_CLIENT_SECRET")
    access_token = await get_access_token_for_user(user_id, client_id, client_secret)
    client = WhoopClient(access_token)

    cycle = None
    recovery = None
    sleep = None
    workout = None

    try:
        cycles = await client.list_cycles(limit=1)
        records = cycles.get("records") or []
        cycle = records[0] if records else None
    except Exception as exc:
        logger.warning("Cycle fetch failed: %s", exc)

    try:
        sleeps = await client.list_sleep(limit=1)
        records = sleeps.get("records") or []
        sleep = records[0] if records else None
    except Exception as exc:
        logger.warning("Sleep fetch failed: %s", exc)

    if cycle and cycle.get("id"):
        try:
            recovery = await client.get_recovery_for_cycle(cycle.get("id"))
        except Exception as exc:
            logger.warning("Recovery fetch failed: %s", exc)

    if recovery is None:
        try:
            recoveries = await client.list_recovery(limit=1)
            records = recoveries.get("records") or []
            recovery = records[0] if records else None
        except Exception as exc:
            logger.warning("Recovery list fetch failed: %s", exc)

    try:
        workouts = await client.list_workouts(limit=1)
        records = workouts.get("records") or []
        workout = records[0] if records else None
    except Exception as exc:
        logger.warning("Workout fetch failed: %s", exc)

    return summarize_whoop_data(cycle, recovery, sleep, workout)


async def build_daily_briefing_payload() -> Dict:
    user_id = os.getenv("WHOOP_DEFAULT_USER_ID")
    if not user_id:
        user_id, _ = get_any_user_token()

    if not user_id:
        return {"error": f"No WHOOP account linked yet. Open the auth URL to connect:\n{_get_auth_url()}"}

    summary = await _fetch_latest_summary(user_id)
    if not summary:
        return {"error": "WHOOP data is unavailable right now. Try again shortly."}

    prompt = (
        "Use the following WHOOP data to draft coach thoughts.\n"
        f"{build_context_snapshot(summary)}"
    )

    session_id = f"whoop-briefing-{user_id}-{uuid.uuid4()}"
    thoughts = await query_hala(
        prompt,
        session_id=session_id,
        system_prompt=BRIEFING_SYSTEM_PROMPT,
        include_history=False,
        start_session=True,
        max_tokens=200,
    )

    return build_briefing_payload(summary, thoughts)
