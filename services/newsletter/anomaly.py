from typing import Any, Dict, Iterable, List, Optional


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return var ** 0.5


def zscore(value: float, values: List[float]) -> float:
    sigma = _std(values)
    if sigma == 0.0:
        return 0.0
    return (value - _mean(values)) / sigma


def flag_anomalies(
    items: Iterable[Dict[str, Any]],
    value_key: str,
    threshold: float = 2.0,
    flag_key: str = "is_anomaly",
    score_key: str = "z_score",
) -> List[Dict[str, Any]]:
    materialized = list(items)
    values = [float(item.get(value_key, 0.0)) for item in materialized if item.get(value_key) is not None]
    for item in materialized:
        value = item.get(value_key)
        if value is None:
            item[flag_key] = False
            item[score_key] = None
            continue
        score = zscore(float(value), values)
        item[score_key] = round(score, 3)
        item[flag_key] = abs(score) >= threshold
    return materialized


def add_change_from_previous(
    items: Iterable[Dict[str, Any]],
    previous: Optional[Iterable[Dict[str, Any]]],
    id_key: str,
    value_key: str,
    change_key: str = "change",
) -> List[Dict[str, Any]]:
    materialized = list(items)
    lookup = {}
    if previous:
        for item in previous:
            lookup[item.get(id_key)] = item

    for item in materialized:
        prev_item = lookup.get(item.get(id_key))
        if not prev_item:
            item[change_key] = None
            continue
        try:
            current = float(item.get(value_key))
            prev_val = float(prev_item.get(value_key))
            item[change_key] = current - prev_val
        except (TypeError, ValueError):
            item[change_key] = None
    return materialized
