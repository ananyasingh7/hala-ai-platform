# Architecture

## Overview
This repo provides integrations and agents around the HalaAI core engine. The main flow is:

1) External data sources (WHOOP) send updates
2) We fetch the latest metrics
3) We summarize the data
4) We ask HalaAI for coaching output
5) We deliver it to Discord (and later other channels)

## Components
- **HalaAI Engine**: primary intelligence engine (external repo)
  - https://github.com/ananyasingh7/HalaAI
- **Discord Agent** (`agents/discord/main.py`)
  - Handles @HalaAI mentions
  - Special health channel behavior
  - Scheduled daily briefing (11:00)
- **WHOOP Server** (`whoop/server.py`)
  - OAuth callback
  - Webhook receiver with signature validation
  - Fetches WHOOP v2 resources and passes summaries to HalaAI
- **Services** (`services/`)
  - `hala_ws.py`: WebSocket client for HalaAI
  - `whoop_client.py`: WHOOP OAuth + REST client
  - `whoop_store.py`: token storage
  - `whoop_briefing.py`: data summarization + Discord embed payloads

## Data flow (WHOOP -> HalaAI -> Discord)
1) WHOOP sends a webhook event (sleep/recovery/workout updated).
2) `whoop/server.py` validates signature and enqueues processing.
3) The server fetches relevant WHOOP v2 resources (sleep/cycle/recovery/workout).
4) `services/whoop_briefing.py` builds a structured summary.
5) `services/hala_ws.py` calls HalaAI with the summary and coaching prompt.
6) Output is sent to Discord via webhook or bot embed.

## Data flow (Discord mention in #health-💪)
1) User mentions @HalaAI in the health channel.
2) Discord agent fetches most recent WHOOP summary.
3) HalaAI generates coaching thoughts.
4) The agent posts a clean embed with a grid-style summary + coaching notes.

## Scheduling
- A daily briefing task runs every minute and posts once at the configured time.
- Controlled by `HEALTH_BRIEFING_TIME` and `HEALTH_TIMEZONE`.

## Security
- WHOOP OAuth uses authorization code flow.
- Webhooks are verified with HMAC SHA-256 using the WHOOP app secret.
- Tokens are stored locally in `whoop/data/tokens.json` (replace with DB later).

## Roadmap
Upcoming bots are tracked in `README.md`.
