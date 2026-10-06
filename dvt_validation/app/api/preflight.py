"""
Preflight API — routes for ZIP upload, result retrieval, and report download.

Pipeline:
    ZIP Service → File Discovery → YAML Parser → SeaTunnel Parser →
    Contract Validator → Cross Validator → Result Builder → Report Generator
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.config.settings import RUNS_DIR
from app.models.preflight_models import (
    CheckSummary,
    OverallStatus,
    PreflightResult,
    Problem,
    Severity,
)
from app.services.contract_validator import validate_contract
from app.services.cross_validator import cross_validate
from app.services.file_discovery_service import discover_files
from app.services.report_service import generate_report
from app.services.seatunnel_parser import parse_seatunnel
from app.services.yaml_parser import parse_yaml
from app.services.zip_service import extract_zip

router = APIRouter(prefix="/api/preflight", tags=["preflight"])


# =========================================================================
# POST /api/preflight/upload
# =========================================================================
@router.post("/upload", response_model=PreflightResult)
async def upload_zip(file: UploadFile = File(...)):
    """
    Accept a migration ZIP, run the full preflight validation pipeline, and
    return a structured result.
    """
    # Read ZIP bytes
    zip_bytes = await file.read()
    original_name = file.filename or "upload.zip"

    all_problems: list[Problem] = []

    # ---- Stage: ZIP Extraction ----
    run_id, dirs, zip_problems = extract_zip(zip_bytes, original_name)
    all_problems.extend(zip_problems)

    if _has_errors(zip_problems):
        return _build_result(run_id, all_problems, stage="zip_extraction", dirs=dirs)

    # ---- Stage: File Discovery ----
    yaml_path, conf_path, disc_problems = discover_files(dirs["extracted"])
    all_problems.extend(disc_problems)

    if _has_errors(disc_problems):
        return _build_result(run_id, all_problems, stage="file_discovery", dirs=dirs)

    assert yaml_path is not None
    assert conf_path is not None

    yaml_name = yaml_path.name
    conf_name = conf_path.name

    # ---- Stage: YAML Parsing ----
    yaml_data, yaml_jobs, yaml_problems = parse_yaml(yaml_path)
    all_problems.extend(yaml_problems)

    if _has_errors(yaml_problems):
        return _build_result(
            run_id, all_problems, stage="yaml_validation",
            dirs=dirs, yaml_file=yaml_name, conf_file=conf_name,
        )

    # ---- Stage: SeaTunnel Parsing ----
    raw_conf, st_jobs, conf_problems = parse_seatunnel(conf_path)
    all_problems.extend(conf_problems)

    if _has_errors(conf_problems):
        return _build_result(
            run_id, all_problems, stage="conf_validation",
            dirs=dirs, yaml_file=yaml_name, conf_file=conf_name,
        )

    # ---- Stage: Contract Validation ----
    contract_problems = validate_contract(yaml_data, yaml_jobs, yaml_name)
    all_problems.extend(contract_problems)

    # Don't gate on contract validation — continue to cross-validation even
    # if there are warnings.

    # ---- Stage: Cross-Validation ----
    if yaml_jobs and st_jobs:
        cross_problems = cross_validate(yaml_jobs, st_jobs, yaml_name, conf_name)
        all_problems.extend(cross_problems)
    elif not yaml_jobs:
        # No YAML jobs — this could be a zero-job contract (all blocked)
        all_problems.append(Problem(
            type="NO_YAML_JOBS",
            severity=Severity.WARNING,
            message="Validation contract declares zero active jobs — nothing to cross-validate.",
            file_a=yaml_name,
            stage="cross_validation",
        ))

    # ---- Build final result ----
    return _build_result(
        run_id, all_problems, stage="preflight",
        dirs=dirs, yaml_file=yaml_name, conf_file=conf_name,
    )


# =========================================================================
# GET /api/preflight/{run_id}
# =========================================================================
@router.get("/{run_id}", response_model=PreflightResult)
async def get_result(run_id: str):
    """Retrieve a previously generated preflight result."""
    result_path = RUNS_DIR / run_id / "reports" / "preflight_result.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    data = json.loads(result_path.read_text(encoding="utf-8"))
    return PreflightResult(**data)


# =========================================================================
# GET /api/preflight/{run_id}/report
# =========================================================================
@router.get("/{run_id}/report", response_class=PlainTextResponse)
async def get_report(run_id: str):
    """Retrieve the Markdown preflight report."""
    report_path = RUNS_DIR / run_id / "reports" / "preflight_report.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Report for run '{run_id}' not found.")
    return report_path.read_text(encoding="utf-8")


# =========================================================================
# Helpers
# =========================================================================

def _has_errors(problems: list[Problem]) -> bool:
    return any(p.severity == Severity.ERROR for p in problems)


def _build_result(
    run_id: str,
    problems: list[Problem],
    stage: str,
    dirs: dict[str, Path] | None = None,
    yaml_file: str | None = None,
    conf_file: str | None = None,
) -> PreflightResult:
    """Build the final PreflightResult from accumulated problems."""
    errors = [p for p in problems if p.severity == Severity.ERROR]
    warnings = [p for p in problems if p.severity == Severity.WARNING]
    infos = [p for p in problems if p.severity == Severity.INFO]

    total = len(problems)
    failed_count = len(errors)
    warning_count = len(warnings)
    passed_count = total - failed_count - warning_count

    status = OverallStatus.FAILED if errors else OverallStatus.SUCCESS

    if status == OverallStatus.SUCCESS:
        msg = "Preflight validation successful. YAML and SeaTunnel configuration are consistent."
    else:
        msg = "Preflight validation failed. Fix the reported mismatches before migration."

    result = PreflightResult(
        run_id=run_id,
        status=status,
        stage=stage,
        summary=CheckSummary(
            total_checks=total,
            passed=passed_count,
            failed=failed_count,
            warnings=warning_count,
        ),
        problems=problems,
        message=msg,
        yaml_file=yaml_file,
        conf_file=conf_file,
    )

    # ---- Persist ----
    if dirs:
        reports_dir = dirs.get("reports", RUNS_DIR / run_id / "reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON result
        result_path = reports_dir / "preflight_result.json"
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        # Generate Markdown report
        generate_report(result, reports_dir)

    return result
