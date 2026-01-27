import os
from typing import Any, Dict, Optional

import httpx


# Frankfurter API (no key required): https://api.frankfurter.dev/v1/latest
EXCHANGE_BASE_URL = os.getenv("EXCHANGE_API_BASE", "https://api.frankfurter.dev/v1")


async def fetch_rate(base: str, target: str) -> Optional[float]:
    base = base.upper()
    target = target.upper()
    url = f"{EXCHANGE_BASE_URL}/latest"
    params = {"base": base, "symbols": target}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    rates = payload.get("rates", {})
    return rates.get(target)


async def convert_currency(amount: Optional[float], base: str, target: str) -> Dict[str, Any]:
    rate = await fetch_rate(base, target)
    converted = None
    if rate is not None and amount is not None:
        try:
            converted = float(amount) * float(rate)
        except (TypeError, ValueError):
            converted = None

    return {
        "base": base.upper(),
        "target": target.upper(),
        "rate": rate,
        "amount": amount,
        "converted": converted,
    }
