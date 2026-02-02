import csv
from pathlib import Path
from typing import Dict, Iterable, Set, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SP500_PATH = ROOT_DIR / "data" / "sp500_constituents.csv"


def _normalize_ticker(symbol: str) -> str:
    return symbol.strip().upper().replace(" ", "")


def _expand_ticker(symbol: str) -> Set[str]:
    base = _normalize_ticker(symbol)
    variants = {base}
    if "." in base:
        variants.add(base.replace(".", "-"))
    if "-" in base:
        variants.add(base.replace("-", "."))
    return variants


def load_sp500_constituents(path: Path | None = None) -> Dict[str, Dict[str, str]]:
    source = path or DEFAULT_SP500_PATH
    if not source.exists():
        return {}

    with source.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        results: Dict[str, Dict[str, str]] = {}
        for row in reader:
            symbol = row.get("Symbol") or row.get("symbol")
            if not symbol:
                continue
            results[_normalize_ticker(symbol)] = {
                "symbol": _normalize_ticker(symbol),
                "name": row.get("Security") or row.get("name") or "",
                "sector": row.get("GICS Sector") or row.get("sector") or "",
            }
        return results


def build_sp500_symbol_set(constituents: Dict[str, Dict[str, str]]) -> Set[str]:
    symbols: Set[str] = set()
    for symbol in constituents.keys():
        symbols.update(_expand_ticker(symbol))
    return symbols


def filter_sp500_earnings(
    earnings: Iterable[Dict[str, str]],
    constituents: Dict[str, Dict[str, str]],
) -> Tuple[Set[str], list]:
    symbol_set = build_sp500_symbol_set(constituents)
    filtered = []
    for item in earnings:
        symbol = item.get("symbol") or ""
        normalized = _normalize_ticker(symbol)
        if normalized in symbol_set:
            enriched = dict(item)
            metadata = constituents.get(normalized)
            if metadata:
                enriched.setdefault("name", metadata.get("name") or "")
                enriched["sector"] = metadata.get("sector") or ""
            filtered.append(enriched)
    return symbol_set, filtered
