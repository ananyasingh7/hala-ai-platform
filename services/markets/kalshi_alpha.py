import os
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import httpx

KALSHI_ALPHA_URL = os.getenv("KALSHI_ALPHA_URL", "https://alpha.kalshi.com/")
UP_ARROW = "\u25b2"
DOWN_ARROW = "\u25bc"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.texts: List[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.texts.append(text)


def _is_number(value: str) -> bool:
    return bool(re.fullmatch(r"-?\d+(\.\d+)?", value))


def _extract_tokens(html: str) -> List[str]:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.texts


def _find_section_start(tokens: List[str], label: str) -> Optional[int]:
    for idx in range(len(tokens) - 1):
        if tokens[idx] == label and tokens[idx + 1].isdigit():
            return idx + 1
    return None


def _parse_ranked_section(
    tokens: List[str],
    start_idx: int,
    end_labels: set,
    limit: int,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    i = start_idx
    while i < len(tokens) and len(items) < limit:
        token = tokens[i]
        if token in end_labels:
            break
        if not token.isdigit():
            i += 1
            continue
        rank = int(token)
        i += 1
        if i >= len(tokens):
            break
        title = tokens[i]
        i += 1
        if i >= len(tokens):
            break
        outcome = tokens[i]
        i += 1

        price = None
        if i < len(tokens) and _is_number(tokens[i]):
            price = float(tokens[i])
            i += 1
            if i < len(tokens) and tokens[i] == "%":
                i += 1

        delta = None
        if i < len(tokens) and tokens[i] in {UP_ARROW, DOWN_ARROW}:
            direction = tokens[i]
            i += 1
            if i < len(tokens) and _is_number(tokens[i]):
                delta = float(tokens[i])
                if direction == DOWN_ARROW:
                    delta = -delta
                i += 1

        items.append(
            {
                "rank": rank,
                "title": title,
                "outcome": outcome,
                "price": price,
                "delta": delta,
            }
        )
    return items


async def fetch_alpha_sections(
    trending_limit: int = 5,
    top_movers_limit: int = 5,
) -> Dict[str, List[Dict[str, Any]]]:
    headers = {"User-Agent": "Mozilla/5.0 (MorningNewsletterBot)"}
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        resp = await client.get(KALSHI_ALPHA_URL)
        resp.raise_for_status()
        html = resp.text

    tokens = _extract_tokens(html)
    trending_start = _find_section_start(tokens, "Trending")
    top_movers_start = _find_section_start(tokens, "Top movers")

    trending = []
    if trending_start is not None:
        trending = _parse_ranked_section(
            tokens,
            trending_start,
            end_labels={"Top movers", "New", "Highest volume"},
            limit=trending_limit,
        )

    top_movers = []
    if top_movers_start is not None:
        top_movers = _parse_ranked_section(
            tokens,
            top_movers_start,
            end_labels={"New", "Highest volume", "Trending"},
            limit=top_movers_limit,
        )

    return {
        "trending": trending,
        "top_movers": top_movers,
    }
