import base64
import hashlib
import hmac
import os
import time
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx

from services.whoop_store import (
    get_token,
    mark_token_refreshed,
    set_token,
    token_is_expired,
)

BASE_URL = "https://api.prod.whoop.com"
AUTH_URL = f"{BASE_URL}/oauth/oauth2/auth"
TOKEN_URL = f"{BASE_URL}/oauth/oauth2/token"


class WhoopClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def _request(self, method: str, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{BASE_URL}{path}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_profile(self) -> Dict:
        return await self._request("GET", "/developer/v2/user/profile/basic")

    async def get_body_measurement(self) -> Dict:
        return await self._request("GET", "/developer/v2/user/measurement/body")

    async def get_cycle(self, cycle_id: str) -> Dict:
        return await self._request("GET", f"/developer/v2/cycle/{cycle_id}")

    async def list_cycles(self, limit: int = 1, start: Optional[str] = None, end: Optional[str] = None, next_token: Optional[str] = None) -> Dict:
        params = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if next_token:
            params["nextToken"] = next_token
        return await self._request("GET", "/developer/v2/cycle", params=params)

    async def get_sleep(self, sleep_id: str) -> Dict:
        return await self._request("GET", f"/developer/v2/activity/sleep/{sleep_id}")

    async def list_sleep(self, limit: int = 1, start: Optional[str] = None, end: Optional[str] = None, next_token: Optional[str] = None) -> Dict:
        params = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if next_token:
            params["nextToken"] = next_token
        return await self._request("GET", "/developer/v2/activity/sleep", params=params)

    async def get_recovery_for_cycle(self, cycle_id: str) -> Dict:
        return await self._request("GET", f"/developer/v2/cycle/{cycle_id}/recovery")

    async def list_recovery(self, limit: int = 1, start: Optional[str] = None, end: Optional[str] = None, next_token: Optional[str] = None) -> Dict:
        params = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if next_token:
            params["nextToken"] = next_token
        return await self._request("GET", "/developer/v2/recovery", params=params)

    async def get_workout(self, workout_id: str) -> Dict:
        return await self._request("GET", f"/developer/v2/activity/workout/{workout_id}")

    async def list_workouts(self, limit: int = 1, start: Optional[str] = None, end: Optional[str] = None, next_token: Optional[str] = None) -> Dict:
        params = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if next_token:
            params["nextToken"] = next_token
        return await self._request("GET", "/developer/v2/activity/workout", params=params)


def build_authorization_url(client_id: str, redirect_uri: str, scopes: list[str], state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()


async def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> Dict:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()


async def get_access_token_for_user(user_id: str, client_id: str, client_secret: str) -> str:
    token_data = get_token(user_id)
    if not token_data:
        raise RuntimeError(f"No WHOOP token stored for user_id={user_id}")

    if token_is_expired(token_data):
        refresh_token_value = token_data.get("refresh_token")
        if not refresh_token_value:
            raise RuntimeError("Access token expired and no refresh token available (missing offline scope).")
        refreshed = await refresh_access_token(client_id, client_secret, refresh_token_value)
        token_data = mark_token_refreshed(user_id, refreshed)

    return token_data.get("access_token")


def store_token_for_user(user_id: str, token_response: Dict) -> None:
    token_data = {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type"),
        "scope": token_response.get("scope"),
        "expires_at": int(time.time()) + int(token_response.get("expires_in", 0)),
    }
    set_token(user_id, token_data)


def validate_webhook_signature(client_secret: str, signature: str, timestamp: str, raw_body: bytes) -> bool:
    message = timestamp.encode("utf-8") + raw_body
    digest = hmac.new(client_secret.encode("utf-8"), message, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)
