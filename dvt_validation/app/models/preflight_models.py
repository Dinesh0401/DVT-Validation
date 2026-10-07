"""
Pydantic models for preflight validation request/response.

Every model is generic — no business values are hardcoded.
"""
from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Severity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class OverallStatus(str, enum.Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Problem descriptor
# ---------------------------------------------------------------------------
class Problem(BaseModel):
    """Single validation problem — always includes *where* and *what*."""

    type: str = Field(..., description="Machine-readable problem category, e.g. COLUMN_MISMATCH")
    severity: Severity = Severity.ERROR
    message: str = ""
    job: str | None = None
    file_a: str | None = None
    path_a: str | None = None
    file_b: str | None = None
    path_b: str | None = None
    expected: Any | None = None
    actual: Any | None = None
    stage: str | None = None


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
class CheckSummary(BaseModel):
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0


# ---------------------------------------------------------------------------
# Preflight Result
# ---------------------------------------------------------------------------
class PreflightResult(BaseModel):
    run_id: str
    status: OverallStatus = OverallStatus.SUCCESS
    can_execute_seatunnel: bool = True
    stage: str = "preflight"
    summary: CheckSummary = CheckSummary()
    problems: list[Problem] = []
    message: str = ""
    yaml_file: str | None = None
    conf_file: str | None = None


# ---------------------------------------------------------------------------
# Internal parsed entities (for cross-validation)
# ---------------------------------------------------------------------------
class SourceEntity(BaseModel):
    """Normalised source description extracted from either file."""
    schema_name: str | None = None
    table_name: str | None = None
    relation: str | None = None
    columns: list[str] = []
    projection_sql: str | None = None
    snapshot_binding: str | None = None


class TargetEntity(BaseModel):
    """Normalised target description extracted from either file."""
    schema_name: str | None = None
    table_name: str | None = None
    relation: str | None = None
    columns: list[str] = []


class TransformEntity(BaseModel):
    """Normalised transformation description."""
    source_table: str | None = None
    result_table: str | None = None
    query: str | None = None


class JobEntity(BaseModel):
    """One logical migration job as seen from a single file."""
    job_id: str
    source: SourceEntity = SourceEntity()
    target: TargetEntity = TargetEntity()
    transforms: list[TransformEntity] = []
    columns: list[str] = []
    checks: list[dict[str, Any]] = []
    snapshot_required: bool = False
    snapshot_binding: str | None = None
    raw_data: dict[str, Any] = {}
