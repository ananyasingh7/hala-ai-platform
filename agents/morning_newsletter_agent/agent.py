import asyncio
import json
import re
from urllib.parse import urlparse
import uuid
from datetime import datetime
from typing import Any, Dict, List

from hala_orchestrator import Agent, MissionState, agent, get_logger

from services.newsletter.anomaly import flag_anomalies
from services.newsletter.cache import read_cache, write_cache
from services.newsletter.compiler import build_newsletter, build_newsletter_discord
from services.newsletter.config import load_newsletter_config
from services.newsletter.sp500 import filter_sp500_earnings, load_sp500_constituents
from services.news.article_fetcher import fetch_article_text


def _format_number(value: Any, suffix: str = "") -> str:
    try:
        return f"{float(value):.2f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def _safe_list(value: Any) -> List:
    if isinstance(value, list):
        return value
    return []


def _normalize_equity(symbol: str) -> str:
    return symbol.strip().upper().replace(" ", "")


def _normalize_text(value: str) -> str:
    return value.lower()


def _collect_portfolio_keywords(
    portfolio_equities: List[str],
    constituents: Dict[str, Dict[str, str]],
) -> List[str]:
    keywords = set()
    for symbol in portfolio_equities:
        normalized = _normalize_equity(symbol)
        if normalized:
            keywords.add(normalized)
        company = constituents.get(normalized, {}).get("name")
        if company:
            keywords.add(company)
    return [item.lower() for item in keywords if item]


def _score_news_item(item: Dict[str, Any], keywords: List[str]) -> int:
    if not keywords:
        return 0
    text = " ".join(
        str(item.get(field) or "")
        for field in ("title", "description", "source")
    ).lower()
    for keyword in keywords:
        if keyword.lower() in text:
            return 1
    return 0


def _is_decided_market(prices: List[float], tolerance: float = 0.0005) -> bool:
    if not prices:
        return False
    for price in prices:
        if price <= tolerance or price >= 1 - tolerance:
            return True
    return False


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _normalize_headline(title: str) -> str:
    lowered = title.lower()
    lowered = re.sub(r"\([^)]*\)", "", lowered)
    lowered = re.sub(r"\$?\d+(\.\d+)?", "", lowered)
    lowered = re.sub(r"price target|stock price|price expected to rise|price target raised|rating", "", lowered)
    lowered = re.sub(r"[^a-z\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _quality_score(item: Dict[str, Any]) -> int:
    source = (item.get("source") or "").lower()
    title = (item.get("title") or "").lower()
    url = (item.get("url") or "")
    domain = _extract_domain(url)
    low_quality = {
        "americanbankingnews",
        "defenseworld",
        "themotleyfool",
        "fool",
        "zacks",
        "insidermonkey",
        "marketbeat",
        "marketwatch",
    }
    score = 0
    if source in low_quality or any(name in domain for name in low_quality):
        score -= 2
    if "price target" in title or "stock price" in title:
        score -= 1
    return score


def _dedupe_headlines(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        title = item.get("title") or ""
        key = _normalize_headline(title)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _safe_json_extract(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"{.*}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


@agent(name="FetchDataAgent", description="Fetches data for the morning newsletter.")
class FetchDataAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        logger = get_logger(self.name, mission_id=state.mission_id, agent=self.name)
        config = load_newsletter_config()
        state.data["newsletter_config"] = config

        async def run_tool(name: str, tool, cache_key: str, kwargs: Dict[str, Any]):
            if not tool:
                logger.warning("Tool missing: %s", name)
                return None
            try:
                result = await tool.run(**kwargs)
                write_cache(cache_key, result)
                return result
            except Exception as exc:
                logger.warning("%s failed: %s", name, exc)
                cached, _ = read_cache(cache_key)
                if cached is not None:
                    logger.info("Using cached data for %s", name)
                    return cached
                return None

        news_tool = self.get_tool("news_api")
        kalshi_alpha_tool = self.get_tool("kalshi_alpha")
        polymarket_tool = self.get_tool("polymarket_api")
        crypto_tool = self.get_tool("crypto_api")
        markets_tool = self.get_tool("markets_api")
        calendar_tool = self.get_tool("calendar_api")
        weather_tool = self.get_tool("openweather")

        markets_cfg = config.get("markets", {}) or {}
        markets_enabled = markets_cfg.get("enabled", True)

        async def _return(value):
            return value

        tasks = {
            "news": run_tool(
                "news",
                news_tool,
                "raw_news",
                config.get("news", {}),
            ),
            "kalshi_alpha": run_tool(
                "kalshi_alpha",
                kalshi_alpha_tool,
                "raw_kalshi_alpha",
                {
                    "trending_limit": config.get("prediction_markets", {}).get("kalshi_trending_limit", 5),
                    "top_movers_limit": config.get("prediction_markets", {}).get("kalshi_top_movers_limit", 5),
                },
            ),
            "polymarket": run_tool(
                "polymarket",
                polymarket_tool,
                "raw_polymarket",
                {
                    "limit": config.get("prediction_markets", {}).get("polymarket_limit", 10),
                    "order": config.get("prediction_markets", {}).get("polymarket_order", "volume24hr"),
                    "ascending": False,
                    "active": True,
                },
            ),
            "crypto": run_tool(
                "crypto",
                crypto_tool,
                "raw_crypto",
                config.get("crypto", {}),
            ),
            "markets": run_tool(
                "markets",
                markets_tool,
                "raw_markets",
                markets_cfg,
            )
            if markets_enabled
            else _return({"futures": [], "indices": []}),
            "calendar": run_tool(
                "calendar",
                calendar_tool,
                "raw_calendar",
                config.get("calendar", {}),
            ),
            "weather": run_tool(
                "weather",
                weather_tool,
                "raw_weather",
                {
                    "city": (config.get("weather", {}) or {}).get("city"),
                    "units": (config.get("weather", {}) or {}).get("units"),
                },
            ),
        }

        results = await asyncio.gather(*tasks.values())
        state.data["raw"] = dict(zip(tasks.keys(), results))
        return state


@agent(name="AnalyzeNewsletterAgent", description="Normalizes and analyzes newsletter data.")
class AnalyzeNewsletterAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        config = state.data.get("newsletter_config") or load_newsletter_config()
        raw = state.data.get("raw") or {}

        sections: Dict[str, Any] = {}
        anomalies: Dict[str, Any] = {}

        news_items = _safe_list(raw.get("news"))
        news_cfg = config.get("news", {}) or {}
        headline_limit = max(
            int(news_cfg.get("min_headlines", 5)),
            int(news_cfg.get("page_size", 8)),
        )
        portfolio_cfg = config.get("portfolio", {}) or {}
        portfolio_equities = [_normalize_equity(sym) for sym in _safe_list(portfolio_cfg.get("equities"))]
        constituents = load_sp500_constituents()
        keywords = _collect_portfolio_keywords(portfolio_equities, constituents)
        if keywords:
            news_items.sort(
                key=lambda item: (_score_news_item(item, keywords), _quality_score(item)),
                reverse=True,
            )
        else:
            news_items.sort(key=_quality_score, reverse=True)
        deduped = _dedupe_headlines(news_items)
        if len(deduped) < headline_limit:
            fallback = [item for item in news_items if item not in deduped]
            deduped.extend(fallback[: max(0, headline_limit - len(deduped))])
        sections["news"] = {"items": deduped[:headline_limit]}

        markets = raw.get("markets") or {}
        futures = _safe_list(markets.get("futures"))
        indices = _safe_list(markets.get("indices"))
        sections["markets"] = {
            "futures": futures,
            "indices": indices,
        }

        crypto = _safe_list(raw.get("crypto"))
        portfolio_crypto = {item.lower() for item in _safe_list(portfolio_cfg.get("crypto_ids")) if item}
        portfolio_crypto_symbols = {item.replace("-", "") for item in portfolio_crypto}
        crypto_table = []
        for coin in crypto:
            symbol = (coin.get("symbol") or "").lower()
            coin_id = (coin.get("id") or "").lower()
            is_portfolio = coin_id in portfolio_crypto or symbol in portfolio_crypto_symbols
            name = coin.get("name") or coin.get("symbol")
            if is_portfolio and name:
                name = f"{name} (Portfolio)"
            crypto_table.append(
                {
                    "name": name,
                    "price": _format_number(coin.get("price")),
                    "change_24h": _format_number(coin.get("change_24h"), "%"),
                    "volume": _format_number(coin.get("volume")),
                    "_raw": coin,
                }
            )
        sections["crypto"] = {"table": crypto_table, "items": crypto}

        kalshi_alpha = raw.get("kalshi_alpha") or {}
        kalshi_trending = _safe_list(kalshi_alpha.get("trending"))
        kalshi_top_movers = _safe_list(kalshi_alpha.get("top_movers"))

        polymarket = _safe_list(raw.get("polymarket"))
        polymarket_prepared = []
        for item in polymarket:
            top_outcomes = _safe_list(item.get("top_outcomes"))
            prices = [outcome.get("price") for outcome in top_outcomes if isinstance(outcome.get("price"), (int, float))]
            if _is_decided_market(prices):
                continue
            formatted_outcomes = []
            for outcome in top_outcomes:
                price = outcome.get("price")
                if isinstance(price, (int, float)):
                    formatted_outcomes.append(f"{outcome.get('outcome')} {price * 100:.1f}%")
            polymarket_prepared.append(
                {
                    "id": item.get("id"),
                    "question": item.get("question"),
                    "top_outcomes": top_outcomes,
                    "top_outcomes_display": ", ".join(formatted_outcomes),
                    "volume_24h": item.get("volume_24h") or item.get("volume"),
                    "url": item.get("url"),
                }
            )

        sections["prediction_markets"] = {
            "kalshi_trending": kalshi_trending,
            "kalshi_top_movers": kalshi_top_movers,
            "polymarket_trending": polymarket_prepared,
        }

        calendar = raw.get("calendar") or {}
        earnings = _safe_list(calendar.get("earnings"))
        economic = _safe_list(calendar.get("economic"))
        _, sp500_earnings = filter_sp500_earnings(earnings, constituents)
        sp500_earnings.sort(
            key=lambda item: (
                0 if _normalize_equity(item.get("symbol") or "") in portfolio_equities else 1,
                item.get("report_date") or "",
            )
        )

        sections["calendar"] = {
            "earnings_sp500": sp500_earnings,
            "economic": economic,
        }

        weather = raw.get("weather") or {}
        if weather:
            sections["weather"] = weather

        z_thresh = float(config.get("anomaly", {}).get("zscore_threshold", 2.0))
        anomalies["crypto"] = [
            item for item in flag_anomalies(crypto, "change_24h", threshold=z_thresh) if item.get("is_anomaly")
        ]
        anomalies["futures"] = [
            item for item in flag_anomalies(futures, "change_percent", threshold=z_thresh) if item.get("is_anomaly")
        ]
        anomalies["indices"] = [
            item for item in flag_anomalies(indices, "change_percent", threshold=z_thresh) if item.get("is_anomaly")
        ]

        state.data["newsletter"] = {
            "generated_at": datetime.utcnow().isoformat(),
            "sections": sections,
            "anomalies": anomalies,
        }
        return state


@agent(name="ComposeNewsletterAgent", description="Composes the newsletter markdown.")
class ComposeNewsletterAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        payload = state.data.get("newsletter") or {}
        sections = payload.get("sections") or {}
        anomalies = payload.get("anomalies") or {}

        hala = self.get_tool("hala_engine")
        config = state.data.get("newsletter_config") or load_newsletter_config()

        if hala:
            session_id = state.metadata.get("newsletter_session_id")
            if not session_id:
                session_id = str(uuid.uuid4())
                state.metadata["newsletter_session_id"] = session_id

            news_items = _safe_list(sections.get("news", {}).get("items"))
            portfolio_cfg = config.get("portfolio", {}) or {}
            portfolio_equities = [
                _normalize_equity(sym) for sym in _safe_list(portfolio_cfg.get("equities"))
            ]
            portfolio_crypto = {item.lower() for item in _safe_list(portfolio_cfg.get("crypto_ids")) if item}

            top_news = news_items[:3]
            article_texts = await asyncio.gather(
                *[fetch_article_text(item.get("url") or "") for item in top_news]
            )
            for item, text in zip(top_news, article_texts):
                if text:
                    item["full_text"] = text
            prediction = sections.get("prediction_markets") or {}
            kalshi_trending = _safe_list(prediction.get("kalshi_trending"))
            kalshi_top_movers = _safe_list(prediction.get("kalshi_top_movers"))
            polymarket_trending = _safe_list(prediction.get("polymarket_trending"))
            calendar = sections.get("calendar") or {}
            sp500_earnings = _safe_list(calendar.get("earnings_sp500"))
            important_limit = int(config.get("calendar", {}).get("important_earnings_limit", 8))
            candidate_earnings = sp500_earnings[: max(important_limit * 6, 30)]

            # Stage 1: summarize full-text articles (top 3) to keep prompt size small.
            full_text_items = [
                {"title": item.get("title"), "full_text": item.get("full_text")}
                for item in top_news
                if item.get("full_text")
            ]
            if full_text_items:
                stage1_prompt = (
                    "Summarize each full_text into 1 concise sentence. Return JSON only.\n"
                    "Return: {\"summaries\": [\"...\", \"...\", ...]} in the same order as input.\n\n"
                    "Input:\n" + json.dumps(full_text_items, ensure_ascii=False)
                )
                stage1_response = await hala.run(
                    prompt=stage1_prompt,
                    session_id=session_id,
                    start_session=True,
                    include_history=False,
                    system_prompt="Return valid JSON only.",
                    max_tokens=400,
                )
                stage1_data = _safe_json_extract(stage1_response)
                stage1_summaries = _safe_list(stage1_data.get("summaries"))
                if not stage1_summaries:
                    stage1_retry = await hala.run(
                        prompt="Return only valid JSON with key summaries.\n\n"
                        + json.dumps(full_text_items, ensure_ascii=False),
                        session_id=session_id,
                        start_session=False,
                        include_history=False,
                        system_prompt="JSON only.",
                        max_tokens=400,
                    )
                    stage1_data = _safe_json_extract(stage1_retry)
                    stage1_summaries = _safe_list(stage1_data.get("summaries"))
                for idx, item in enumerate(full_text_items):
                    if idx < len(stage1_summaries):
                        title = item.get("title")
                        for news_item in news_items:
                            if news_item.get("title") == title:
                                news_item["full_text_summary"] = stage1_summaries[idx]

            llm_payload = {
                "news": [
                    {
                        "title": item.get("title"),
                        "source": item.get("source"),
                        "description": item.get("description"),
                        "full_text_summary": item.get("full_text_summary"),
                    }
                    for item in news_items
                ],
                "kalshi_trending": [
                    {
                        "title": item.get("title"),
                        "outcome": item.get("outcome"),
                        "price": item.get("price"),
                    }
                    for item in kalshi_trending
                ],
                "kalshi_top_movers": [
                    {
                        "title": item.get("title"),
                        "outcome": item.get("outcome"),
                        "price": item.get("price"),
                    }
                    for item in kalshi_top_movers
                ],
                "polymarket_trending": [
                    {
                        "question": item.get("question"),
                        "top_outcomes": item.get("top_outcomes"),
                    }
                    for item in polymarket_trending
                ],
                "sp500_earnings": [
                    {
                        "symbol": item.get("symbol"),
                        "name": item.get("name"),
                        "report_date": item.get("report_date"),
                    }
                    for item in candidate_earnings
                ],
                "portfolio_equities": portfolio_equities,
                "portfolio_crypto": sorted(portfolio_crypto),
            }

            prompt = (
                "You are drafting a morning market newsletter. Return JSON only.\n"
                "Tasks:\n"
                "1) For each news item, write a 1-sentence summary.\n"
                "2) For each prediction market item, write a 1-sentence summary explaining the market and the odds.\n"
                "3) From the S&P 500 earnings list, pick the most important companies (max "
                f"{important_limit}) and provide a short reason.\n\n"
                "Always prioritize the portfolio equities if they appear in the earnings list.\n"
                "If full_text_summary is provided for a news item, use it for the summary. Otherwise use title/description.\n"
                "Return JSON with keys:\n"
                "- news_summaries: list of summaries in the same order as input news\n"
                "- kalshi_trending_summaries: list in same order as input kalshi_trending\n"
                "- kalshi_top_movers_summaries: list in same order as input kalshi_top_movers\n"
                "- polymarket_trending_summaries: list in same order as input polymarket_trending\n"
                "- important_earnings: list of objects {symbol, name, report_date, reason}\n\n"
                "Input data:\n"
                + json.dumps(llm_payload, ensure_ascii=False)
            )

            response = await hala.run(
                prompt=prompt,
                session_id=session_id,
                start_session=True,
                include_history=False,
                system_prompt="Return valid JSON only. No markdown or commentary.",
                max_tokens=700,
            )
            summary_data = _safe_json_extract(response)
            if not summary_data:
                retry = await hala.run(
                    prompt="Return only valid JSON matching the required keys. No extra text.\n\n"
                    + json.dumps(llm_payload, ensure_ascii=False),
                    session_id=session_id,
                    start_session=False,
                    include_history=False,
                    system_prompt="JSON only.",
                    max_tokens=700,
                )
                summary_data = _safe_json_extract(retry)

            news_summaries = _safe_list(summary_data.get("news_summaries"))
            for idx, item in enumerate(news_items):
                if idx < len(news_summaries):
                    item["summary"] = news_summaries[idx]
                elif item.get("description"):
                    item["summary"] = str(item.get("description")).split(".")[0].strip()

            kalshi_summaries = _safe_list(summary_data.get("kalshi_trending_summaries"))
            for idx, item in enumerate(kalshi_trending):
                if idx < len(kalshi_summaries):
                    item["summary"] = kalshi_summaries[idx]

            top_movers_summaries = _safe_list(summary_data.get("kalshi_top_movers_summaries"))
            for idx, item in enumerate(kalshi_top_movers):
                if idx < len(top_movers_summaries):
                    item["summary"] = top_movers_summaries[idx]

            poly_summaries = _safe_list(summary_data.get("polymarket_trending_summaries"))
            for idx, item in enumerate(polymarket_trending):
                if idx < len(poly_summaries):
                    item["summary"] = poly_summaries[idx]

            important_earnings = _safe_list(summary_data.get("important_earnings"))
            if important_earnings:
                calendar["important_earnings"] = important_earnings
            else:
                calendar["important_earnings"] = sp500_earnings[:important_limit]
            sections["calendar"] = calendar
        else:
            calendar = sections.get("calendar") or {}
            if not calendar.get("important_earnings"):
                sp500_earnings = _safe_list(calendar.get("earnings_sp500"))
                important_limit = int(config.get("calendar", {}).get("important_earnings_limit", 8))
                calendar["important_earnings"] = sp500_earnings[:important_limit]
                sections["calendar"] = calendar

        content = build_newsletter(
            sections=sections,
            anomalies=anomalies,
            generated_at=payload.get("generated_at"),
        )
        discord_content = build_newsletter_discord(
            sections=sections,
            anomalies=anomalies,
            generated_at=payload.get("generated_at"),
        )
        state.final_output = content
        state.data["discord_content"] = discord_content
        return state


@agent(name="DeliverNewsletterAgent", description="Delivers newsletter to disk/email.")
class DeliverNewsletterAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        delivery = self.get_tool("delivery")
        config = state.data.get("newsletter_config") or load_newsletter_config()
        if not delivery:
            return state

        today = datetime.utcnow().date().isoformat()
        filename = f"morning_newsletter_{today}.md"
        output_dir = config.get("delivery", {}).get("output_dir", "reports/morning_newsletter")

        result = await delivery.run(
            content=state.final_output or "",
            discord_content=state.data.get("discord_content") or "",
            output_dir=output_dir,
            filename=filename,
            subject=f"Morning Newsletter ({today})",
        )
        state.data["delivery"] = result
        return state
