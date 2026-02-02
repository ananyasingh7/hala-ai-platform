import os
from typing import Any, Dict, List

import httpx

KALSHI_API_BASE = os.getenv("KALSHI_API_BASE", "https://api.elections.kalshi.com/trade-api/v2")


async def fetch_markets(status: str = "open", limit: int = 20) -> List[Dict[str, Any]]:
    endpoint = f"{KALSHI_API_BASE}/markets"
    params = {
        "status": status,
        "limit": limit,
    }

    headers = {}
    api_key = os.getenv("KALSHI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    markets = []
    for item in payload.get("markets", []) or []:
        markets.append(
            {
                "id": item.get("ticker"),
                "event_ticker": item.get("event_ticker"),
                "title": item.get("title"),
                "subtitle": item.get("subtitle"),
                "yes_bid": item.get("yes_bid"),
                "yes_ask": item.get("yes_ask"),
                "no_bid": item.get("no_bid"),
                "no_ask": item.get("no_ask"),
                "last_price": item.get("last_price"),
                "volume": item.get("volume"),
                "open_interest": item.get("open_interest"),
                "close_time": item.get("close_time"),
                "url": item.get("url"),
            }
        )
    return markets
