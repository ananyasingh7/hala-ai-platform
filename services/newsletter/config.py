from pathlib import Path
from typing import Any, Dict

import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "newsletter.yaml"
PORTFOLIO_CONFIG_PATH = ROOT_DIR / "config" / "portfolio.yaml"

DEFAULTS: Dict[str, Any] = {
    "news": {
        "category": "business",
        "query": None,
        "country": "us",
        "page_size": 8,
        "min_headlines": 5,
    },
    "markets": {
        "enabled": True,
        "futures": ["ES=F", "NQ=F", "YM=F", "CL=F", "GC=F"],
        "indices": ["^N225", "^FTSE", "^GDAXI"],
    },
    "crypto": {
        "ids": ["bitcoin", "ethereum", "solana", "ripple", "dogecoin"],
        "per_page": 5,
    },
    "prediction_markets": {
        "kalshi_trending_limit": 5,
        "kalshi_top_movers_limit": 5,
        "polymarket_limit": 8,
        "polymarket_order": "volume24hr",
    },
    "calendar": {
        "days_ahead": 7,
        "indicators": ["UNEMPLOYMENT", "INFLATION", "GDP"],
        "important_earnings_limit": 8,
    },
    "anomaly": {
        "zscore_threshold": 2.0,
    },
    "delivery": {
        "output_dir": "demo/reports/morning_newsletter",
    },
    "portfolio": {
        "equities": [],
        "crypto_ids": [],
    },
    "weather": {
        "city": "New York, US",
        "units": "imperial",
    },
}


def load_newsletter_config(path: Path | None = None) -> Dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        merged = DEFAULTS.copy()
    else:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            merged = DEFAULTS.copy()
        else:
            merged = DEFAULTS.copy()
            for key, value in raw.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value

    if PORTFOLIO_CONFIG_PATH.exists():
        try:
            portfolio_raw = yaml.safe_load(PORTFOLIO_CONFIG_PATH.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            portfolio_raw = None
        if isinstance(portfolio_raw, dict):
            portfolio = portfolio_raw.get("portfolio", portfolio_raw)
            if isinstance(portfolio, dict):
                merged["portfolio"] = {**(merged.get("portfolio") or {}), **portfolio}
    return merged
