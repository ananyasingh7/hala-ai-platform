from typing import Any, Dict, List, Optional

from hala_orchestrator.tools import Tool

from services.calendar.alpha_vantage import fetch_earnings_calendar, fetch_economic_indicators
from services.crypto.coingecko import fetch_top_coins
from services.markets.alpha_vantage import fetch_quotes
from services.markets.kalshi import fetch_markets as fetch_kalshi_markets
from services.markets.kalshi_alpha import fetch_alpha_sections
from services.markets.polymarket import fetch_markets as fetch_polymarket_markets
from services.news.news_client import fetch_news
from services.newsletter.delivery import send_discord, send_email, write_markdown


class NewsTool(Tool):
    name = "news_api"

    async def run(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return await fetch_news(
            category=kwargs.get("category"),
            query=kwargs.get("query"),
            country=kwargs.get("country"),
            language=kwargs.get("language"),
            page_size=int(kwargs.get("page_size") or 10),
        )


class KalshiTool(Tool):
    name = "kalshi_api"

    async def run(self, **kwargs: Any) -> List[Dict[str, Any]]:
        status = kwargs.get("status", "active")
        limit = int(kwargs.get("limit") or 20)
        return await fetch_kalshi_markets(status=status, limit=limit)


class KalshiAlphaTool(Tool):
    name = "kalshi_alpha"

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        trending_limit = int(kwargs.get("trending_limit") or 5)
        top_movers_limit = int(kwargs.get("top_movers_limit") or 5)
        return await fetch_alpha_sections(
            trending_limit=trending_limit,
            top_movers_limit=top_movers_limit,
        )


class PolymarketTool(Tool):
    name = "polymarket_api"

    async def run(self, **kwargs: Any) -> List[Dict[str, Any]]:
        limit = int(kwargs.get("limit") or 20)
        active = kwargs.get("active", True)
        order = kwargs.get("order")
        ascending = kwargs.get("ascending")
        closed = kwargs.get("closed")
        return await fetch_polymarket_markets(
            limit=limit,
            active=active,
            order=order,
            ascending=ascending,
            closed=closed,
        )


class CryptoTool(Tool):
    name = "crypto_api"

    async def run(self, **kwargs: Any) -> List[Dict[str, Any]]:
        ids = kwargs.get("ids")
        if isinstance(ids, str):
            ids = [item.strip() for item in ids.split(",") if item.strip()]
        per_page = int(kwargs.get("per_page") or (len(ids) if ids else 10))
        return await fetch_top_coins(
            vs_currency=kwargs.get("vs_currency") or "usd",
            per_page=per_page,
            ids=ids,
        )


class MarketsTool(Tool):
    name = "markets_api"

    async def run(self, **kwargs: Any) -> Dict[str, List[Dict[str, Any]]]:
        futures = kwargs.get("futures") or []
        indices = kwargs.get("indices") or []
        rate_limit = kwargs.get("rate_limit_sec")
        if isinstance(rate_limit, str):
            try:
                rate_limit = float(rate_limit)
            except ValueError:
                rate_limit = None

        futures_quotes = await fetch_quotes(list(futures), rate_limit_sec=rate_limit) if futures else []
        indices_quotes = await fetch_quotes(list(indices), rate_limit_sec=rate_limit) if indices else []
        return {
            "futures": futures_quotes,
            "indices": indices_quotes,
        }


class CalendarTool(Tool):
    name = "calendar_api"

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        days_ahead = int(kwargs.get("days_ahead") or 7)
        indicators = kwargs.get("indicators")
        if isinstance(indicators, str):
            indicators = [item.strip() for item in indicators.split(",") if item.strip()]
        earnings = await fetch_earnings_calendar(days_ahead=days_ahead)
        econ = await fetch_economic_indicators(indicators=indicators)
        return {
            "earnings": earnings,
            "economic": econ,
        }


class DeliveryTool(Tool):
    name = "delivery"

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        content = kwargs.get("content") or ""
        discord_content = kwargs.get("discord_content") or content
        output_dir = kwargs.get("output_dir") or "demo/reports/morning_newsletter"
        filename = kwargs.get("filename") or "newsletter.md"
        subject = kwargs.get("subject") or "Morning Newsletter"
        output_path = write_markdown(output_dir, filename, content)
        recipient = send_email(subject, content)
        discord_sent = await send_discord(discord_content)
        return {
            "output_path": output_path,
            "email_recipient": recipient,
            "discord_sent": discord_sent,
        }
