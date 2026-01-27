from pathlib import Path
from typing import Optional

from hala_orchestrator.loader import create_runtime

from orchestration.tooling import get_tool_factories


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "orchestrator.yaml"


async def run_mission_from_config(
    mission_name: str,
    objective_override: Optional[str] = None,
    config_path: Optional[str | Path] = None,
    mission_id: Optional[str] = None,
):
    path = Path(config_path) if config_path else _default_config_path()
    runtime = create_runtime(path, tool_factories=get_tool_factories())
    return await runtime.run_mission(
        mission_name=mission_name,
        objective_override=objective_override,
        mission_id=mission_id,
    )
