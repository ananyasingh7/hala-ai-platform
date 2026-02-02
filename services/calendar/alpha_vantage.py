import csv
import io
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

ALPHA_VANTAGE_BASE = os.getenv("ALPHA_VANTAGE_BASE", "https://www.alphavantage.co/query")


def _parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


async def fetch_earnings_calendar(days_ahead: int = 7) -> List[Dict[str, Any]]:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ALPHA_VANTAGE_API_KEY")

    params = {
        "function": "EARNINGS_CALENDAR",
        "apikey": api_key,
        "horizon": "3month",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        raw = resp.text

    # Alpha Vantage returns CSV for earnings calendar.
    rows: List[Dict[str, Any]] = []
    if "text/csv" in content_type or raw.lstrip().startswith("symbol"):
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
    else:
        try:
            payload = resp.json()
            rows = payload.get("data", []) or []
        except ValueError:
            rows = []

    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    upcoming = []
    for row in rows:
        report_date = _parse_date(row.get("reportDate") or row.get("report_date") or "")
        if report_date is None:
            continue
        if not (today <= report_date <= cutoff):
            continue
        upcoming.append(
            {
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "report_date": report_date.isoformat(),
                "estimate": row.get("estimate"),
                "currency": row.get("currency"),
            }
        )
    return upcoming


async def fetch_economic_indicators(indicators: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ALPHA_VANTAGE_API_KEY")

    indicators = indicators or ["UNEMPLOYMENT", "INFLATION", "GDP"]
    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name in indicators:
            params = {
                "function": name,
                "apikey": api_key,
            }
            resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data", []) or []
            latest = data[0] if data else {}
            results.append(
                {
                    "indicator": name,
                    "date": latest.get("date"),
                    "value": latest.get("value"),
                }
            )
    return results
