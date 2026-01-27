# Travel Planner Agent (Demo #1)

This is the first agent built for the platform using the orchestrator SDK.
It demonstrates real tool integration with the HalaAI engine and zero mock data.

## What it does

- Extracts travel parameters from the user request using HalaAI:
  - `city`
  - `base_currency`
  - `target_currency`
  - `amount`
- Fetches live weather from OpenWeatherMap
- Fetches live exchange rates from ExchangeRates API
- Produces a concise travel brief using HalaAI

## Tools Used

- `hala_engine` (WebSocket tool to the local HalaAI engine)
- `openweather` (OpenWeatherMap API)
- `exchange_rates` (Frankfurter API, no key required)

## Configuration

Configured in `config/orchestrator.yaml`:

```
missions:
  travel_planner:
    planner:
      type: static
      steps:
        - TravelPlannerAgent
```

## Notes

- This agent is intentionally simple and serves as the first real, end-to-end demo.
- It requires `HALA_WS_URL` to be set and the HalaAI engine running.
- If OpenWeather returns 401, set `OPENWEATHER_API_KEY` in your environment.
- Exchange rates use Frankfurter (no key required).
