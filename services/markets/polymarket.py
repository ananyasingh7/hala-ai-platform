import json
import os
from typing import Any, Dict, List, Optional

import httpx

POLYMARKET_API_BASE = os.getenv("POLYMARKET_API_BASE", "https://gamma-api.polymarket.com")


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []
    return []


def _extract_yes_price(outcomes: List[str], prices: List[Any]) -> Optional[float]:
    if not outcomes or not prices:
        return None
    pairs = list(zip(outcomes, prices))
    for name, price in pairs:
        if str(name).strip().lower() in {"yes", "true"}:
            return _safe_float(price)
    return _safe_float(pairs[0][1])


def _extract_top_outcomes(outcomes: List[str], prices: List[Any], top_n: int = 2) -> List[Dict[str, Any]]:
    pairs = []
    for name, price in zip(outcomes, prices):
        numeric = _safe_float(price)
        if numeric is None:
            continue
        pairs.append({"outcome": str(name), "price": numeric})
    pairs.sort(key=lambda item: item["price"], reverse=True)
    return pairs[:top_n]


async def fetch_markets(
    limit: int = 20,
    active: bool | None = True,
    order: Optional[str] = None,
    ascending: Optional[bool] = None,
    closed: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    endpoint = f"{POLYMARKET_API_BASE}/markets"
    params = {
        "limit": limit,
    }
    if active is not None:
        params["active"] = str(active).lower()
    if closed is not None:
        params["closed"] = str(closed).lower()
    if order:
        params["order"] = order
    if ascending is not None:
        params["ascending"] = str(ascending).lower()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint, params=params)
        resp.raise_for_status()
        payload = resp.json()

    markets = []
    for item in payload or []:
        outcomes = _normalize_list(item.get("outcomes"))
        prices = _normalize_list(item.get("outcomePrices"))
        yes_price = _extract_yes_price(outcomes, prices)
        top_outcomes = _extract_top_outcomes(outcomes, prices, top_n=2)
        markets.append(
            {
                "id": item.get("id") or item.get("conditionId"),
                "question": item.get("question"),
                "slug": item.get("slug"),
                "outcomes": outcomes,
                "outcome_prices": prices,
                "yes_price": yes_price,
                "top_outcomes": top_outcomes,
                "volume": item.get("volumeNum") or item.get("volume"),
                "volume_24h": item.get("volume24hr") or item.get("volume24Hour"),
                "liquidity": item.get("liquidityNum") or item.get("liquidity"),
                "end_date": item.get("endDate"),
                "url": item.get("url"),
            }
        )
    return markets
