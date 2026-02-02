# Hala AI Platform

This repository is the integration layer around the **primary HalaAI engine**:

- Primary engine: https://github.com/ananyasingh7/HalaAI

It connects external data sources (WHOOP), local services, and Discord agents to HalaAI for proactive coaching and interventions.

## What this repo does
- Runs a Discord bot that can answer questions and produce daily WHOOP briefings.
- Hosts a local WHOOP OAuth + webhook server to ingest updates.
- Pushes structured summaries to HalaAI via WebSocket.

## Current components
- `tools/discord` - Discord bot (mentions, daily briefing, health channel behavior)
- `tools/whoop/server.py` - WHOOP OAuth + webhook receiver
- `agents/travel_planner_agent` - First demo agent (weather + currency + HalaAI)
- `agents/morning_newsletter_agent` - Morning newsletter (news, markets, crypto, calendar, weather)
- `scheduler/` - Simple daily scheduler scripts
- `services/` - reusable clients (WHOOP + HalaAI WS)
- `audio/` - microphone + speaker components (work in progress)
- `ui/` - lightweight web chat UI (ChatGPT-style)

## Upcoming bots
- News/Prediction Markets Bot
- Discord Voice Bot
- Stonks Bot
- Anomaly Bot
- Chat UI (lightweight)
- HalaAI Code (CLI)
- Things-to-do Bot

## Quick start (local)
1) Install deps:
```
pip install -r requirements.txt
```

2) Configure `.env` with your tokens and URLs:
```
DISCORD_TOKEN=...
HALA_WS_URL=ws://localhost:8000/ws/chat/v2
WHOOP_CLIENT_ID=...
WHOOP_CLIENT_SECRET=...
WHOOP_REDIRECT_URI=https://<your-tunnel>.trycloudflare.com/whoop/callback
WHOOP_PUBLIC_BASE_URL=https://<your-tunnel>.trycloudflare.com
WHOOP_DEFAULT_USER_ID=...
DISCORD_HEALTH_WEBHOOK_URL=...
HEALTH_CHANNEL_ID=...
HEALTH_BRIEFING_TIME=11:00
HEALTH_TIMEZONE=America/Los_Angeles
```

3) Start the WHOOP server:
```
python tools/whoop/server.py
```

4) Start the Discord bot:
```
python tools/discord/main.py
```

5) Start the lightweight chat UI:



```bash

cd ui

npm install

npm run dev

```

Then open http://localhost:5173

Optional overrides:
```
HALA_API_BASE=http://localhost:8000
HALA_WS_URL=ws://localhost:8000/ws/chat/v2
```

## Morning Newsletter (local)
1) Set env vars (minimum):
```
NEWS_API_KEY=...
NEWSDATA_API_KEY=...        # optional
ALPHA_VANTAGE_API_KEY=...
OPENWEATHER_API_KEY=...
HALA_WS_URL=ws://localhost:8000/ws/chat/v2
```

2) (Optional) Set portfolio in a private file (gitignored):
```
config/portfolio.yaml
```

3) Optional delivery:
```
DISCORD_NEWSLETTER_WEBHOOK_URL=...
DISCORD_WEBHOOK_URL=...     # fallback key if you prefer
NEWSLETTER_SMTP_HOST=...
NEWSLETTER_SMTP_PORT=587
NEWSLETTER_SMTP_USER=...
NEWSLETTER_SMTP_PASSWORD=...
NEWSLETTER_EMAIL_FROM=...
NEWSLETTER_EMAIL_TO=...
```

4) Run once (writes Markdown + sends to Discord/email):
```
python demo/run_morning_newsletter.py
```

Output:
- `demo/reports/morning_newsletter/`

## Scheduler (daily)
```
python scheduler/morning_newsletter_scheduler.py
```

Defaults:
- 6:05 AM America/New_York (override with `NEWSLETTER_TZ`, `NEWSLETTER_HOUR`, `NEWSLETTER_MINUTE`)

## Notes
- Use a Cloudflare Quick Tunnel for HTTPS during local development.
- OAuth redirects and webhooks must be HTTPS and publicly reachable.
- If your tunnel URL changes, update the WHOOP app settings + `.env`.
