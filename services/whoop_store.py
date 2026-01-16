import json
import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "whoop" / "data"
TOKENS_PATH = DATA_DIR / "tokens.json"

_LOCK = threading.Lock()


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_raw() -> Dict:
    _ensure_data_dir()
    if not TOKENS_PATH.exists():
        return {"users": {}}
    with TOKENS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_raw(data: Dict) -> None:
    _ensure_data_dir()
    tmp_path = TOKENS_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    tmp_path.replace(TOKENS_PATH)


def get_token(user_id: str) -> Optional[Dict]:
    with _LOCK:
        data = _load_raw()
        return data.get("users", {}).get(user_id)


def set_token(user_id: str, token_data: Dict) -> None:
    with _LOCK:
        data = _load_raw()
        data.setdefault("users", {})[user_id] = token_data
        _write_raw(data)


def get_any_user_token() -> Tuple[Optional[str], Optional[Dict]]:
    with _LOCK:
        data = _load_raw()
        users = data.get("users", {})
        if not users:
            return None, None
        user_id, token = next(iter(users.items()))
        return user_id, token


def mark_token_refreshed(user_id: str, token_response: Dict) -> Dict:
    token_data = _normalize_token_response(token_response)
    set_token(user_id, token_data)
    return token_data


def _normalize_token_response(token_response: Dict) -> Dict:
    expires_in = token_response.get("expires_in")
    expires_at = None
    if expires_in is not None:
        expires_at = int(time.time()) + int(expires_in)
    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type"),
        "scope": token_response.get("scope"),
        "expires_at": expires_at,
    }


def token_is_expired(token_data: Dict, leeway_seconds: int = 60) -> bool:
    expires_at = token_data.get("expires_at")
    if not expires_at:
        return False
    return time.time() >= (float(expires_at) - leeway_seconds)
