# Hala AI Platform

This repository is the integration layer around the **primary HalaAI engine**:

- Primary engine: https://github.com/ananyasingh7/HalaAI

It connects external data sources (WHOOP), local services, and Discord agents to HalaAI for proactive coaching and interventions.

## What this repo does
- Runs a Discord bot that can answer questions and produce daily WHOOP briefings.
- Hosts a local WHOOP OAuth + webhook server to ingest updates.
- Pushes structured summaries to HalaAI via WebSocket.

## Current components
- `agents/discord` - Discord bot (mentions, daily briefing, health channel behavior)
- `agents/whoop/server.py` - WHOOP OAuth + webhook receiver
- `services/` - reusable clients (WHOOP + HalaAI WS)
- `audio/` - microphone + speaker components (work in progress)

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
python agents/whoop/server.py
```

4) Start the Discord bot:
```
python agents/discord/main.py
```

## Notes
- Use a Cloudflare Quick Tunnel for HTTPS during local development.
- OAuth redirects and webhooks must be HTTPS and publicly reachable.
- If your tunnel URL changes, update the WHOOP app settings + `.env`.
