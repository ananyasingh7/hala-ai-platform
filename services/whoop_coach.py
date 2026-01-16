import json
from datetime import datetime
from typing import Dict, Optional


SYSTEM_PROMPT = (
    "You are HalaAI, a proactive health coach."
    " Use the WHOOP data to interpret how the user is doing today,"
    " identify risks (overtraining, low recovery, poor sleep),"
    " and recommend specific adjustments to training and schedule."
    " Keep it concise (2-5 sentences)."
    " If data is missing or inconclusive, ask one targeted question."
)


def _format_dt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return value


def build_context_snapshot(summary: Dict) -> str:
    return json.dumps(summary, indent=2, sort_keys=True)


def build_user_prompt(summary: Dict) -> str:
    return (
        "WHOOP data snapshot (most recent):\n"
        f"{build_context_snapshot(summary)}\n\n"
        "Respond as the Active Coach. If recovery or sleep is poor,"
        " recommend lowering intensity and rescheduling as needed."
    )


def summarize_whoop_data(
    cycle: Optional[Dict],
    recovery: Optional[Dict],
    sleep: Optional[Dict],
    workout: Optional[Dict],
) -> Dict:
    summary: Dict = {}

    if cycle:
        summary["cycle"] = {
            "id": cycle.get("id"),
            "start": _format_dt(cycle.get("start")),
            "end": _format_dt(cycle.get("end")),
            "score_state": cycle.get("score_state"),
            "score": cycle.get("score"),
        }

    if recovery:
        summary["recovery"] = {
            "score_state": recovery.get("score_state"),
            "score": recovery.get("score"),
        }

    if sleep:
        summary["sleep"] = {
            "id": sleep.get("id"),
            "start": _format_dt(sleep.get("start")),
            "end": _format_dt(sleep.get("end")),
            "nap": sleep.get("nap"),
            "score_state": sleep.get("score_state"),
            "score": sleep.get("score"),
        }

    if workout:
        summary["workout"] = {
            "id": workout.get("id"),
            "sport_name": workout.get("sport_name"),
            "start": _format_dt(workout.get("start")),
            "end": _format_dt(workout.get("end")),
            "score_state": workout.get("score_state"),
            "score": workout.get("score"),
        }

    return summary
