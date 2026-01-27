# Config-Driven Orchestrator Flow

This document describes how `hala-ai-platform` runs orchestration using a config file.

## Overview

- Config file: `config/orchestrator.yaml`
- Loader: `hala_orchestrator.loader.create_runtime`
- Platform runtime helper: `orchestration/runner.py`

The SDK reads the YAML, resolves environment variables, builds tools + agents, and executes the mission plan.

## Steps

1) **Load config**
   - `config/orchestrator.yaml` is read
   - `${ENV_VAR}` placeholders are resolved

2) **Instantiate tools**
   - `hala_engine` tool is created from `hala_ws` factory
   - `openweather` and `exchange_rates` tools are created from their factories

3) **Instantiate agents**
   - Agents are imported by class path
   - Tool bindings are injected
   - Runtime limits/timeouts are applied

4) **Plan mission**
   - Mission `travel_planner` uses a static planner
   - Steps: `TravelPlannerAgent`

5) **Execute**
   - `FlowRouter` runs each agent with timeouts
   - Agents call the Hala engine tool as needed
   - Output is written to `state.final_output`

## Runtime Entry (Platform)

Use the platform helper (async):

```python
from orchestration.runner import run_mission_from_config

state = await run_mission_from_config("travel_planner")
print(state.final_output)
```

## Notes

- Tools can be extended by adding new factories in `orchestration/tooling.py`
- Additional missions can be added to the YAML without code changes
- Ensure `HALA_WS_URL` is set so the Hala engine tool can connect
- Set `OPENWEATHER_API_KEY` to enable weather lookups
