# Morning Newsletter Agent

## Overview
The Morning Newsletter agent generates a daily market brief with headlines, prediction markets, crypto, earnings, and weather. It uses HalaAI for structured summaries and can deliver the result to Discord (webhook) and email (SMTP).

## What it includes
- **Headlines**: Top business/tech headlines with one‑sentence summaries.
- **Prediction markets**:
  - Kalshi Trending + Top Movers (from `alpha.kalshi.com`)
  - Polymarket Trending (Gamma API, 24h volume sorted)
  - Markets with 100% odds are filtered out.
- **Crypto snapshot**: Prices, 24h change, volume. Portfolio coins are tagged.
- **Earnings (S&P 500 Focus)**: Upcoming earnings, prioritized by portfolio + HalaAI.
- **Economic calendar**: Key releases (GDP, inflation, unemployment).
- **Weather**: Current conditions for the configured city.

## HalaAI summary flow
Two-stage flow to reduce token pressure:
1) **Top 3 articles** → fetch full text → HalaAI 1‑sentence summaries.
2) **Full newsletter** → HalaAI combines headline summaries + prediction market summaries + important earnings picks.

## Config files
- `config/newsletter.yaml` (public, committed)
  - watchlists, thresholds, output dir, weather city
- `config/portfolio.yaml` (private, gitignored)
  - portfolio equities + crypto ids

Example portfolio file:
```yaml
portfolio:
  equities:
    - AAPL
    - NVDA
  crypto_ids:
    - bitcoin
    - ripple
```

## Required environment variables
- `NEWS_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `OPENWEATHER_API_KEY`
- `HALA_WS_URL` (e.g., `ws://localhost:8000/ws/chat/v2`)

Optional:
- `NEWSDATA_API_KEY`
- `DISCORD_NEWSLETTER_WEBHOOK_URL` (preferred)
- `DISCORD_WEBHOOK_URL` (fallback)
- `NEWSLETTER_SMTP_HOST`
- `NEWSLETTER_SMTP_PORT`
- `NEWSLETTER_SMTP_USER`
- `NEWSLETTER_SMTP_PASSWORD`
- `NEWSLETTER_EMAIL_FROM`
- `NEWSLETTER_EMAIL_TO`

## Run manually
```bash
python demo/run_morning_newsletter.py
```

Output:
- Markdown file: `demo/reports/morning_newsletter/`
- Discord: formatted message (if webhook configured)

## Scheduler (daily)
```bash
python scheduler/morning_newsletter_scheduler.py
```

Defaults:
- 6:05 AM America/New_York  
- Override with `NEWSLETTER_TZ`, `NEWSLETTER_HOUR`, `NEWSLETTER_MINUTE`

## Security and privacy
- Portfolio is in a **gitignored** file: `config/portfolio.yaml`
- Discord delivery uses a webhook stored in `.env` (never committed)
- Newsletter state output does **not** include the webhook URL

## Troubleshooting
- **Weather missing**: check `OPENWEATHER_API_KEY` and `weather.city` in `config/newsletter.yaml`.
- **HalaAI errors**: ensure HalaAI server is running (`~/hala-ai/run_server.py`) and `HALA_WS_URL` is correct.
- **No Discord post**: ensure `DISCORD_NEWSLETTER_WEBHOOK_URL` is set; rotate if leaked.
