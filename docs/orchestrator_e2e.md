# Orchestrator E2E Flow (MVP)

This document describes the end-to-end flow for the Hala Orchestrator MVP, as used by `hala-ai-platform`.

## Objective

Provide a market briefing using the custom orchestration SDK.

## Components

- **Orchestrator SDK** (`hala-ai-orchestrator`)
  - `MissionState`: shared clipboard
  - `Agent`: base class for workers
  - `Planner`: returns a plan (ordered agent list)
  - `FlowRouter`: executes the plan
  - `Tools`: async helpers (mocked for MVP)

- **Platform Agents** (`hala-ai-platform/agents/orchestration`)
  - `NewsAgent`: reads headlines into state
  - `CryptoAgent`: reads prices and adds insight
  - `WriterAgent`: synthesizes final report

## Flow (MVP)

1) **User input**
   - `example_flow.py` sends: `"Give me a market briefing."`

2) **Planner**
   - `SimplePlanner` returns `["NewsAgent", "CryptoAgent", "WriterAgent"]`

3) **NewsAgent**
    - Uses `StaticNewsTool`
    - Appends `Fed rates holding steady.` to `state.findings`
    - Stores headlines in `state.data["news"]`
    - Sends mock headlines to HalaAI for a short analysis (`state.data["news_llm"]`)

4) **CryptoAgent**
    - Uses `StaticPriceTool`
    - Stores BTC price in `state.data["btc_price"]`
    - Adds interpretation to `state.findings`
    - Sends mock price + headlines to HalaAI (`state.data["crypto_llm"]`)

5) **WriterAgent**
   - Reads `state.findings` + `state.data`
   - Writes markdown report to `state.final_output`

6) **Output**
   - `example_flow.py` prints the report

## How to Run

From `hala-ai-platform`:

```
python example_flow.py
```

## Notes

- Tools are mocked for now; swap them with real HalaAI tools later.
- The orchestrator SDK provides decorators, context managers, and structured logging.
