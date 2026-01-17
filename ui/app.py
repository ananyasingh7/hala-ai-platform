import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

HALA_API_BASE = os.getenv("HALA_API_BASE", "http://localhost:8000").rstrip("/")
HALA_WS_URL = os.getenv("HALA_WS_URL", "ws://localhost:8000/ws/chat/v2")

app = FastAPI(title="HalaAI Platform UI")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config")
async def get_config():
    return {
        "ws_url": HALA_WS_URL,
    }


async def _proxy_get(path: str, params: dict | None = None):
    url = f"{HALA_API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or exc.response.reason_phrase
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc


@app.get("/api/sessions")
async def list_sessions():
    return await _proxy_get("/data/sessions")


@app.get("/api/session")
async def get_session(session_id: str = Query(..., description="Session UUID")):
    return await _proxy_get("/data/session", params={"session_id": session_id})


async def _proxy_delete(path: str, params: dict | None = None):
    url = f"{HALA_API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or exc.response.reason_phrase
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc


@app.delete("/api/session")
async def delete_session(session_id: str = Query(..., description="Session UUID")):
    return await _proxy_delete("/data/session", params={"session_id": session_id})
