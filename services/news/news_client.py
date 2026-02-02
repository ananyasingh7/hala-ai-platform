import asyncio
import os
from typing import Any, Dict, List, Optional

import httpx

NEWSAPI_BASE = os.getenv("NEWSAPI_BASE", "https://newsapi.org/v2")
NEWSDATA_BASE = os.getenv("NEWSDATA_BASE", "https://newsdata.io/api/1")


async def _fetch_newsapi(
    api_key: str,
    category: Optional[str],
    query: Optional[str],
    country: Optional[str],
    language: Optional[str],
    page_size: int,
) -> List[Dict[str, Any]]:
    endpoint = f"{NEWSAPI_BASE}/top-headlines"
    params: Dict[str, Any] = {"pageSize": page_size}
    if category:
        params["category"] = category
    if query:
        params["q"] = query
    if country:
        params["country"] = country
    if language:
        params["language"] = language

    headers = {"X-Api-Key": api_key}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    articles = []
    for item in payload.get("articles", []) or []:
        source = item.get("source") or {}
        articles.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "source": source.get("name"),
                "published_at": item.get("publishedAt"),
                "description": item.get("description") or item.get("content"),
            }
        )
    return articles


async def _fetch_newsdata(
    api_key: str,
    category: Optional[str],
    query: Optional[str],
    country: Optional[str],
    language: Optional[str],
    page_size: int,
) -> List[Dict[str, Any]]:
    endpoint = f"{NEWSDATA_BASE}/news"
    params: Dict[str, Any] = {
        "apikey": api_key,
        "size": page_size,
    }
    if category:
        params["category"] = category
    if query:
        params["q"] = query
    if country:
        params["country"] = country
    if language:
        params["language"] = language

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint, params=params)
        resp.raise_for_status()
        payload = resp.json()

    articles = []
    for item in payload.get("results", []) or []:
        articles.append(
            {
                "title": item.get("title"),
                "url": item.get("link"),
                "source": item.get("source_id"),
                "published_at": item.get("pubDate"),
                "description": item.get("description") or item.get("content"),
            }
        )
    return articles


async def fetch_news(
    category: Optional[str] = None,
    query: Optional[str] = None,
    country: Optional[str] = "us",
    language: Optional[str] = None,
    page_size: int = 10,
) -> List[Dict[str, Any]]:
    newsapi_key = os.getenv("NEWS_API_KEY")
    newsdata_key = os.getenv("NEWSDATA_API_KEY")

    tasks = []
    sources = []
    if newsapi_key:
        tasks.append(
            _fetch_newsapi(
                newsapi_key,
                category=category,
                query=query,
                country=country,
                language=language,
                page_size=page_size,
            )
        )
        sources.append("NewsAPI")
    if newsdata_key:
        tasks.append(
            _fetch_newsdata(
                newsdata_key,
                category=category,
                query=query,
                country=country,
                language=language,
                page_size=page_size,
            )
        )
        sources.append("NewsData")

    if not tasks:
        raise RuntimeError("Missing NEWS_API_KEY and NEWSDATA_API_KEY")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: List[Dict[str, Any]] = []
    errors: List[str] = []
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            errors.append(f"{source} error: {result}")
            continue
        items.extend(result)

    if not items:
        raise RuntimeError("; ".join(errors) if errors else "No news results")

    seen = set()
    deduped: List[Dict[str, Any]] = []
    for item in items:
        key = (item.get("url") or item.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    min_size = max(5, page_size)
    return deduped[:min_size]
