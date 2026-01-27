# Orchestrator E2E Flow (MVP)

This document describes the end-to-end flow for the Hala Orchestrator MVP, as used by `hala-ai-platform`.

## Objective

Provide a travel planning response using the custom orchestration SDK.

## Components

- **Orchestrator SDK** (`hala-ai-orchestrator`)
  - `MissionState`: shared clipboard
  - `Agent`: base class for workers
  - `Planner`: returns a plan (ordered agent list)
  - `FlowRouter`: executes the plan
  - `Tools`: async helpers (real APIs)

- **Platform Orchestration** (`hala-ai-platform/orchestration`)
  - Defines agents and runtime wiring for the orchestrator SDK

## Flow (MVP)

1) **User input**
   - A platform entrypoint calls `run_mission_from_config("travel_planner")`

2) **Planner**
   - Mission planner returns `TravelPlannerAgent`

3) **Agent**
   - `TravelPlannerAgent` calls OpenWeather + Frankfurter + HalaAI

4) **Output**
   - The caller receives results from `MissionState` (e.g., `final_output`, `data`, `findings`)

## Notes

- The orchestrator SDK provides decorators, context managers, and structured logging.
