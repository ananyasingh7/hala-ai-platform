import json
import time
from pathlib import Path
from typing import Any, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT_DIR / "data" / "newsletter_cache"


def _cache_path(section: str) -> Path:
    safe = section.replace("/", "_").replace(" ", "_")
    return CACHE_DIR / f"{safe}.json"


def read_cache(section: str) -> Tuple[Optional[dict], Optional[float]]:
    path = _cache_path(section)
    if not path.exists():
        return None, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, None
    return raw.get("payload"), raw.get("timestamp")


def write_cache(section: str, payload: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(section)
    data = {
        "timestamp": time.time(),
        "payload": payload,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
