import asyncio
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.logging import get_logger
from services.hala_ws import query_hala
from services.whoop_client import (
    WhoopClient,
    build_authorization_url,
    exchange_code_for_token,
    get_access_token_for_user,
    store_token_for_user,
    validate_webhook_signature,
)
from services.whoop_coach import SYSTEM_PROMPT, build_user_prompt, summarize_whoop_data
from services.whoop_briefing import build_briefing_payload, build_discord_embed_dict

# Load environment variables from repo root
load_dotenv(dotenv_path=ROOT_DIR / ".env")

logger = get_logger("WhoopServer")
app = FastAPI()

STATE_TTL_SECONDS = 600
STATE_STORE: Dict[str, float] = {}
SESSION_BY_USER: Dict[str, str] = {}


def _get_env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def _get_scopes() -> list[str]:
    raw = os.getenv(
        "WHOOP_SCOPES",
        "read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement",
    )
    return [scope.strip() for scope in raw.split() if scope.strip()]


def _clean_states() -> None:
    now = time.time()
    expired = [state for state, ts in STATE_STORE.items() if now - ts > STATE_TTL_SECONDS]
    for state in expired:
        STATE_STORE.pop(state, None)


def _get_or_create_session(user_id: str) -> Tuple[str, bool]:
    session_id = SESSION_BY_USER.get(user_id)
    if session_id:
        return session_id, False
    session_id = f"whoop-{user_id}"
    SESSION_BY_USER[user_id] = session_id
    return session_id, True


@app.get("/whoop/auth")
async def whoop_auth():
    client_id = _get_env("WHOOP_CLIENT_ID")
    redirect_uri = _get_env("WHOOP_REDIRECT_URI")
    scopes = _get_scopes()

    _clean_states()
    state = str(uuid.uuid4())
    STATE_STORE[state] = time.time()

    auth_url = build_authorization_url(client_id, redirect_uri, scopes, state)
    return RedirectResponse(auth_url)


@app.get("/whoop/callback")
async def whoop_callback(code: Optional[str] = None, state: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")
    if not state or state not in STATE_STORE:
        raise HTTPException(status_code=400, detail="Invalid or missing state")
    STATE_STORE.pop(state, None)

    client_id = _get_env("WHOOP_CLIENT_ID")
    client_secret = _get_env("WHOOP_CLIENT_SECRET")
    redirect_uri = _get_env("WHOOP_REDIRECT_URI")

    token_response = await exchange_code_for_token(client_id, client_secret, redirect_uri, code)
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Token response missing access_token")

    profile = await WhoopClient(access_token).get_profile()
    user_id = profile.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Profile response missing user_id")

    store_token_for_user(user_id, token_response)
    return JSONResponse({"status": "ok", "user_id": user_id})


@app.post("/whoop/webhook")
async def whoop_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-WHOOP-Signature")
    timestamp = request.headers.get("X-WHOOP-Signature-Timestamp")

    if not signature or not timestamp:
        raise HTTPException(status_code=400, detail="Missing signature headers")

    try:
        timestamp_int = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signature timestamp")

    tolerance = int(os.getenv("WHOOP_WEBHOOK_TOLERANCE_SECONDS", "300"))
    if abs(int(time.time()) - timestamp_int) > tolerance:
        raise HTTPException(status_code=401, detail="Stale webhook signature")

    client_secret = _get_env("WHOOP_CLIENT_SECRET")
    if not validate_webhook_signature(client_secret, signature, timestamp, raw_body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    asyncio.create_task(_process_webhook(payload))
    return JSONResponse({"status": "accepted"})


async def _process_webhook(payload: Dict) -> None:
    try:
        user_id = payload.get("user_id")
        event_type = payload.get("type")
        event_id = payload.get("id")
        if not user_id or not event_type:
            logger.warning("Webhook payload missing user_id or type: %s", payload)
            return

        client_id = _get_env("WHOOP_CLIENT_ID")
        client_secret = _get_env("WHOOP_CLIENT_SECRET")
        access_token = await get_access_token_for_user(user_id, client_id, client_secret)
        client = WhoopClient(access_token)

        cycle = None
        recovery = None
        sleep = None
        workout = None

        if event_type.startswith("sleep") and event_id:
            sleep = await client.get_sleep(event_id)
            cycle_id = sleep.get("cycle_id")
            if cycle_id:
                cycle = await client.get_cycle(cycle_id)
                try:
                    recovery = await client.get_recovery_for_cycle(cycle_id)
                except Exception as exc:
                    logger.warning("Recovery fetch failed for cycle %s: %s", cycle_id, exc)

        elif event_type.startswith("recovery") and event_id:
            sleep = await client.get_sleep(event_id)
            cycle_id = sleep.get("cycle_id") if sleep else None
            if cycle_id:
                cycle = await client.get_cycle(cycle_id)
                recovery = await client.get_recovery_for_cycle(cycle_id)

        elif event_type.startswith("workout") and event_id:
            workout = await client.get_workout(event_id)

        if cycle is None:
            try:
                cycles = await client.list_cycles(limit=1)
                records = cycles.get("records") or []
                cycle = records[0] if records else None
            except Exception as exc:
                logger.warning("Cycle list fetch failed: %s", exc)

        if sleep is None:
            try:
                sleeps = await client.list_sleep(limit=1)
                records = sleeps.get("records") or []
                sleep = records[0] if records else None
            except Exception as exc:
                logger.warning("Sleep list fetch failed: %s", exc)

        if recovery is None:
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

        if workout is None:
            try:
                workouts = await client.list_workouts(limit=1)
                records = workouts.get("records") or []
                workout = records[0] if records else None
            except Exception as exc:
                logger.warning("Workout list fetch failed: %s", exc)

        summary = summarize_whoop_data(cycle, recovery, sleep, workout)
        if not summary:
            logger.info("No data available to coach from WHOOP.")
            return

        user_prompt = build_user_prompt(summary)
        session_id, start_session = _get_or_create_session(user_id)

        response = await query_hala(
            user_prompt,
            session_id=session_id,
            system_prompt=SYSTEM_PROMPT,
            include_history=False,
            start_session=start_session,
        )

        logger.info("Coach response for user %s: %s", user_id, response)

        await _send_discord_webhook(summary, response)

    except Exception as exc:
        logger.exception("Failed to process WHOOP webhook: %s", exc)


async def _send_discord_webhook(summary: Dict, thoughts: str) -> None:
    webhook_url = os.getenv("DISCORD_HEALTH_WEBHOOK_URL")
    if not webhook_url:
        return

    payload = build_briefing_payload(summary, thoughts)
    embed = build_discord_embed_dict(payload)
    data = {"embeds": [embed]}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=data)
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Discord webhook failed: %s", exc)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("WHOOP_PORT", "8765"))
    uvicorn.run("tools.whoop.server:app", host="0.0.0.0", port=port, reload=False)
