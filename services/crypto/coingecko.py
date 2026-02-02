import os
from typing import Any, Dict, List, Optional

import httpx

COINGECKO_BASE = os.getenv("COINGECKO_BASE", "https://api.coingecko.com/api/v3")


async def fetch_top_coins(
    vs_currency: str = "usd",
    per_page: int = 10,
    ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    endpoint = f"{COINGECKO_BASE}/coins/markets"
    params: Dict[str, Any] = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "price_change_percentage": "24h",
    }
    if ids:
        id_map = {"xrp": "ripple"}
        normalized = [id_map.get(item.lower(), item) for item in ids]
        params["ids"] = ",".join(normalized)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint, params=params)
        resp.raise_for_status()
        payload = resp.json()

    coins = []
    for item in payload or []:
        coins.append(
            {
                "id": item.get("id"),
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "price": item.get("current_price"),
                "market_cap": item.get("market_cap"),
                "volume": item.get("total_volume"),
                "change_24h": item.get("price_change_percentage_24h"),
            }
        )
    return coins
