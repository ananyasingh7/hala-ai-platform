import html as html_lib
import re
from typing import Optional

import httpx


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<(script|style|noscript)[^>]*>.*?</\\1>", " ", text, flags=re.S | re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html_lib.unescape(cleaned)
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    return cleaned


async def fetch_article_text(url: str, max_chars: int = 2000) -> Optional[str]:
    if not url:
        return None
    headers = {"User-Agent": "Mozilla/5.0 (MorningNewsletterBot)"}
    try:
        async with httpx.AsyncClient(timeout=12.0, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                return None
            raw = resp.text
    except Exception:
        return None

    text = _strip_html(raw)
    if not text or len(text) < 200:
        return None
    return text[:max_chars]
