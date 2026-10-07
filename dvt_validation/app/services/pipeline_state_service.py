"""
Pipeline State Service — manage migration lifecycle & entry gates.

States:
    UPLOADED → PREFLIGHT_SUCCESS → MIGRATION_SUCCESS → DVT_RUNNING → DVT_PASSED / DVT_FAILED

Persisted in ``runs/<run_id>/pipeline_state.json``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from app.config.settings import RUNS_DIR


class PipelineStageState(str, Enum):
    UPLOADED = "UPLOADED"
    PREFLIGHT_SUCCESS = "PREFLIGHT_SUCCESS"
    PREFLIGHT_BLOCKED = "PREFLIGHT_BLOCKED"
    MIGRATION_RUNNING = "MIGRATION_RUNNING"
    MIGRATION_SUCCESS = "MIGRATION_SUCCESS"
    MIGRATION_FAILED = "MIGRATION_FAILED"
    DVT_RUNNING = "DVT_RUNNING"
    DVT_PASSED = "DVT_PASSED"
    DVT_FAILED = "DVT_FAILED"
    NOT_STARTED = "NOT_STARTED"


def get_pipeline_state(run_id: str) -> dict[str, Any]:
    """Retrieve the current pipeline state for a run ID."""
    state_file = RUNS_DIR / run_id / "pipeline_state.json"
    if not state_file.exists():
        return {
            "run_id": run_id,
            "preflight": "NOT_STARTED",
            "migration": "NOT_STARTED",
            "dvt": "NOT_STARTED",
            "overall_status": "NOT_STARTED",
            "can_execute_dvt": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    return json.loads(state_file.read_text(encoding="utf-8"))


def save_pipeline_state(run_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update and persist pipeline state for a run ID."""
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state_file = run_dir / "pipeline_state.json"

    current = get_pipeline_state(run_id)
    current.update(updates)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Determine readiness for DVT
    preflight_ok = current.get("preflight") in ("SUCCESS", "READY", "REVIEW", "PREFLIGHT_SUCCESS")
    migration_ok = current.get("migration") in ("SUCCESS", "MIGRATION_SUCCESS")
    current["can_execute_dvt"] = preflight_ok and migration_ok

    # Determine overall status
    if current.get("dvt") == "DVT_PASSED" or current.get("dvt") == "PASSED":
        current["overall_status"] = "SUCCESS"
    elif current.get("dvt") in ("DVT_FAILED", "FAILED"):
        current["overall_status"] = "FAILED"
    elif current.get("migration") in ("MIGRATION_FAILED", "FAILED"):
        current["overall_status"] = "MIGRATION_FAILED"
    elif current.get("preflight") in ("BLOCKED", "FAILED"):
        current["overall_status"] = "PREFLIGHT_BLOCKED"
    else:
        current["overall_status"] = current.get("dvt", current.get("migration", current.get("preflight", "IN_PROGRESS")))

    state_file.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current
