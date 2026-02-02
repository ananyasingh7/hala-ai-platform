from datetime import datetime
import os
from typing import Any, Dict, List, Optional


def _format_bullets(items: List[str]) -> str:
    if not items:
        return "- N/A"
    return "\n".join(f"- {item}" for item in items)


def _format_headlines(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "- N/A"
    lines: List[str] = []
    for item in items:
        title = item.get("title") or "Untitled"
        source = item.get("source") or "Unknown"
        summary = item.get("summary")
        lines.append(f"- {title} ({source})")
        if item.get("full_text_summary"):
            lines.append("  - (Full-text summarized)")
        if summary:
            lines.append(f"  - {summary}")
    return "\n".join(lines)


def _format_table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    if not rows:
        return "N/A"
    header = " | ".join(columns)
    sep = " | ".join(["---"] * len(columns))
    lines = [header, sep]
    for row in rows:
        lines.append(" | ".join(str(row.get(col, "")) for col in columns))
    return "\n".join(lines)


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _abbrev_number(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return str(value)
    abs_val = abs(number)
    suffixes = ["", "K", "M", "B", "T"]
    idx = 0
    while abs_val >= 1000 and idx < len(suffixes) - 1:
        abs_val /= 1000.0
        idx += 1
    formatted = f"{abs_val:.2f}{suffixes[idx]}"
    return formatted if number >= 0 else f"-{formatted}"


def _format_currency(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return str(value)
    return f"${number:,.2f}"


def _format_table_code(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    if not rows:
        return "N/A"
    formatted_rows = []
    for row in rows:
        formatted_rows.append([str(row.get(col, "")) for col in columns])
    widths = [len(col) for col in columns]
    for row in formatted_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    sep = "-+-".join("-" * widths[i] for i in range(len(columns)))
    lines = [header, sep]
    for row in formatted_rows:
        lines.append(" | ".join(row[i].ljust(widths[i]) for i in range(len(columns))))
    return "```\n" + "\n".join(lines) + "\n```"


def _format_timestamp(value: Optional[str]) -> str:
    tz_name = os.getenv("NEWSLETTER_TZ", "America/New_York")
    tzinfo = None
    try:
        from zoneinfo import ZoneInfo

        tzinfo = ZoneInfo(tz_name)
    except Exception:
        tzinfo = None

    if value:
        cleaned = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            dt = datetime.utcnow()
    else:
        dt = datetime.utcnow()

    if tzinfo:
        try:
            dt = dt.astimezone(tzinfo)
        except ValueError:
            dt = dt.replace(tzinfo=tzinfo)
    return dt.strftime("%a, %b %d, %Y %I:%M %p %Z").strip()


def _format_prediction_items(items: List[Dict[str, Any]], label: str) -> List[str]:
    if not items:
        return []
    lines = [f"### {label}"]
    for item in items:
        title = item.get("title") or item.get("question") or "Untitled"
        outcome = item.get("outcome") or item.get("top_outcomes_display") or "N/A"
        price = item.get("price")
        if isinstance(price, (int, float)):
            odds = f"{price:.1f}%"
        else:
            odds = None
        if odds and outcome != "N/A":
            headline = f"- {title} — {outcome} ({odds})"
        elif outcome != "N/A":
            headline = f"- {title} — {outcome}"
        else:
            headline = f"- {title}"
        lines.append(headline)
        summary = item.get("summary")
        if summary:
            lines.append(f"  - {summary}")
    return lines


def _format_earnings(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "- N/A"
    lines: List[str] = []
    for item in items:
        symbol = item.get("symbol") or ""
        name = item.get("name") or ""
        report_date = item.get("report_date") or ""
        reason = item.get("reason") or item.get("summary")
        if name:
            line = f"- {symbol} ({name}) — {report_date}"
        else:
            line = f"- {symbol} — {report_date}"
        lines.append(line)
        if reason:
            lines.append(f"  - {reason}")
    return "\n".join(lines)


def build_newsletter(
    sections: Dict[str, Any],
    anomalies: Dict[str, Any],
    generated_at: Optional[str] = None,
    intro: Optional[str] = None,
    takeaways: Optional[List[str]] = None,
) -> str:
    timestamp = _format_timestamp(generated_at)
    lines = [
        "# Morning Newsletter",
        f"Generated: {timestamp}",
        "",
    ]

    weather = sections.get("weather") or {}
    if weather:
        units = weather.get("units")
        unit_label = "°F" if units == "imperial" else "°C"
        wind_unit = "mph" if units == "imperial" else "m/s"
        temp = weather.get("temperature")
        feels = weather.get("feels_like")
        humidity = weather.get("humidity")
        wind = weather.get("wind_speed")
        description = weather.get("description") or "N/A"
        city = weather.get("city") or "Unknown"
        country = weather.get("country") or ""
        location = f"{city}, {country}".strip(", ")
        details = (
            f"{description} | {temp}{unit_label} (feels {feels}{unit_label}) | "
            f"Humidity {humidity}% | Wind {wind} {wind_unit}"
        )
        lines.append(f"## Weather — {location}")
        lines.append(f"- {details}")
        lines.append("")
    else:
        lines.append("## Weather")
        lines.append("- Unavailable (check OPENWEATHER_API_KEY and weather.city)")
        lines.append("")

    if intro:
        lines.extend([intro, ""])  # intro can be a short paragraph

    if takeaways:
        lines.append("## Top Takeaways")
        lines.append(_format_bullets(takeaways))
        lines.append("")

    news = sections.get("news") or {}
    lines.append("## Headlines")
    lines.append(_format_headlines(news.get("items", [])))
    lines.append("")

    markets = sections.get("markets") or {}
    futures = markets.get("futures", [])
    indices = markets.get("indices", [])
    if futures:
        lines.append("## US Futures")
        lines.append(_format_table(futures, ["symbol", "price", "change_percent"]))
        lines.append("")
    if indices:
        lines.append("## International Markets")
        lines.append(_format_table(indices, ["symbol", "price", "change_percent"]))
        lines.append("")

    prediction = sections.get("prediction_markets") or {}
    prediction_lines: List[str] = []
    prediction_lines.extend(
        _format_prediction_items(prediction.get("kalshi_trending", []), "Kalshi Trending")
    )
    prediction_lines.extend(
        _format_prediction_items(prediction.get("kalshi_top_movers", []), "Kalshi Top Movers")
    )
    prediction_lines.extend(
        _format_prediction_items(prediction.get("polymarket_trending", []), "Polymarket Trending")
    )
    if prediction_lines:
        lines.append("## Prediction Markets")
        lines.extend(prediction_lines)
        lines.append("")

    crypto = sections.get("crypto") or {}
    if crypto.get("table"):
        lines.append("## Crypto Snapshot")
        lines.append(_format_table(crypto.get("table", []), ["name", "price", "change_24h", "volume"]))
        lines.append("")

    calendar = sections.get("calendar") or {}
    important_earnings = calendar.get("important_earnings") or []
    economic = calendar.get("economic") or []
    if important_earnings:
        lines.append("## Earnings (S&P 500 Focus)")
        lines.append(_format_earnings(important_earnings))
        lines.append("")
    if economic:
        lines.append("## Economic Calendar")
        econ_lines = [
            f"{item.get('indicator')}: {item.get('value')} ({item.get('date')})"
            for item in economic
        ]
        lines.append(_format_bullets(econ_lines))
        lines.append("")

    sports = sections.get("sports") or {}
    if sports.get("bullets"):
        lines.append("## Sports")
        lines.append(_format_bullets(sports.get("bullets", [])))
        lines.append("")

    if anomalies:
        lines.append("## Anomalies")
        summary = []
        for name, items in anomalies.items():
            if not items:
                continue
            summary.append(f"{name}: {len(items)} flagged")
        lines.append(_format_bullets(summary))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_newsletter_discord(
    sections: Dict[str, Any],
    anomalies: Dict[str, Any],
    generated_at: Optional[str] = None,
) -> str:
    timestamp = _format_timestamp(generated_at)
    lines = [
        "**Morning Newsletter**",
        f"Generated: {timestamp}",
        "",
    ]

    weather = sections.get("weather") or {}
    if weather:
        units = weather.get("units")
        unit_label = "°F" if units == "imperial" else "°C"
        wind_unit = "mph" if units == "imperial" else "m/s"
        temp = weather.get("temperature")
        feels = weather.get("feels_like")
        humidity = weather.get("humidity")
        wind = weather.get("wind_speed")
        description = weather.get("description") or "N/A"
        city = weather.get("city") or "Unknown"
        country = weather.get("country") or ""
        location = f"{city}, {country}".strip(", ")
        lines.append(f"**Weather — {location}**")
        lines.append(
            f"- {description} | {temp}{unit_label} (feels {feels}{unit_label}) | "
            f"Humidity {humidity}% | Wind {wind} {wind_unit}"
        )
        lines.append("")
    else:
        lines.append("**Weather**")
        lines.append("- Unavailable (check OPENWEATHER_API_KEY and weather.city)")
        lines.append("")

    news = sections.get("news") or {}
    lines.append("**Headlines**")
    if news.get("items"):
        for item in news.get("items", []):
            title = item.get("title") or "Untitled"
            source = item.get("source") or "Unknown"
            lines.append(f"- {title} ({source})")
            if item.get("full_text_summary"):
                lines.append("  - (Full-text summarized)")
            summary = item.get("summary")
            if summary:
                lines.append(f"  - {summary}")
    else:
        lines.append("- N/A")
    lines.append("")

    prediction = sections.get("prediction_markets") or {}
    prediction_lines: List[str] = []
    prediction_lines.extend(
        _format_prediction_items(prediction.get("kalshi_trending", []), "Kalshi Trending")
    )
    prediction_lines.extend(
        _format_prediction_items(prediction.get("kalshi_top_movers", []), "Kalshi Top Movers")
    )
    prediction_lines.extend(
        _format_prediction_items(prediction.get("polymarket_trending", []), "Polymarket Trending")
    )
    if prediction_lines:
        lines.append("**Prediction Markets**")
        lines.extend(prediction_lines)
        lines.append("")

    crypto = sections.get("crypto") or {}
    if crypto.get("table"):
        formatted = []
        for item in crypto.get("table", []):
            formatted.append(
                {
                    "name": item.get("name"),
                    "price": _format_currency(item.get("price")),
                    "change_24h": item.get("change_24h"),
                    "volume": _abbrev_number(item.get("volume")),
                }
            )
        lines.append("**Crypto Snapshot**")
        lines.append(_format_table_code(formatted, ["name", "price", "change_24h", "volume"]))
        lines.append("")

    calendar = sections.get("calendar") or {}
    important_earnings = calendar.get("important_earnings") or []
    economic = calendar.get("economic") or []
    if important_earnings:
        lines.append("**Earnings (S&P 500 Focus)**")
        lines.append(_format_earnings(important_earnings))
        lines.append("")
    if economic:
        lines.append("**Economic Calendar**")
        econ_lines = [
            f"{item.get('indicator')}: {item.get('value')} ({item.get('date')})"
            for item in economic
        ]
        lines.append(_format_bullets(econ_lines))
        lines.append("")

    if anomalies:
        summary = []
        for name, items in anomalies.items():
            if not items:
                continue
            summary.append(f"{name}: {len(items)} flagged")
        if summary:
            lines.append("**Anomalies**")
            lines.append(_format_bullets(summary))
            lines.append("")

    return "\n".join(lines).strip() + "\n"
