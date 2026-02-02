import asyncio
import os
from typing import Any, Dict, List, Optional

import httpx

ALPHA_VANTAGE_BASE = os.getenv("ALPHA_VANTAGE_BASE", "https://www.alphavantage.co/query")


def _parse_change_percent(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    cleaned = str(value).replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


async def fetch_global_quote(symbol: str, api_key: str) -> Dict[str, Any]:
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
        resp.raise_for_status()
        payload = resp.json()

    quote = payload.get("Global Quote", {})
    return {
        "symbol": symbol,
        "price": _parse_float(quote.get("05. price")),
        "change": _parse_float(quote.get("09. change")),
        "change_percent": _parse_change_percent(quote.get("10. change percent")),
        "latest_trading_day": quote.get("07. latest trading day"),
        "raw": quote,
    }


async def fetch_quotes(symbols: List[str], rate_limit_sec: Optional[float] = None) -> List[Dict[str, Any]]:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ALPHA_VANTAGE_API_KEY")

    delay = rate_limit_sec
    if delay is None:
        delay = float(os.getenv("ALPHA_VANTAGE_RATE_LIMIT_SEC", "12"))

    results = []
    for idx, symbol in enumerate(symbols):
        results.append(await fetch_global_quote(symbol, api_key))
        if idx < len(symbols) - 1:
            await asyncio.sleep(delay)
    return results
