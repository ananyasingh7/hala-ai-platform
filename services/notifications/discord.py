import os

import httpx


DISCORD_NEWSLETTER_WEBHOOK_URL = os.getenv("DISCORD_NEWSLETTER_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL")


def _chunk_message(text: str, limit: int = 1900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        chunk = text[start:end]
        if end < len(text):
            last_break = chunk.rfind("\n")
            if last_break > 200:
                end = start + last_break
                chunk = text[start:end]
        chunks.append(chunk)
        start = end
    return chunks


async def send_discord_message(message: str) -> bool:
    if not DISCORD_NEWSLETTER_WEBHOOK_URL:
        return False
    chunks = _chunk_message(message)
    async with httpx.AsyncClient(timeout=10.0) as client:
        for chunk in chunks:
            resp = await client.post(
                DISCORD_NEWSLETTER_WEBHOOK_URL,
                json={"content": chunk},
            )
            resp.raise_for_status()
    return True
