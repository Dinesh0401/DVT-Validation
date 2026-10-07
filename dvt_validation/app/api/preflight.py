"""
Preflight API — routes for ZIP upload, result retrieval, status check, and report download.

Pipeline:
    ZIP Service → File Discovery → YAML Parser → SeaTunnel Parser →
    Contract Validator → Cross Validator → DVT Generator → Result Builder → Report Generator
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from app.config.settings import RUNS_DIR
from app.models.preflight_models import (
    CheckSummary,
    JobEntity,
    OverallStatus,
    PreflightResult,
    Problem,
    Severity,
)
from app.services.contract_validator import validate_contract
from app.services.cross_validator import cross_validate
from app.services.dvt_generator_service import generate_dvt_manifest
from app.services.dvt_validator_service import execute_dvt_validation
from app.services.file_discovery_service import discover_files
from app.services.pipeline_state_service import get_pipeline_state, save_pipeline_state
from app.services.report_service import generate_report
from app.services.seatunnel_parser import parse_seatunnel
from app.services.yaml_parser import parse_yaml
from app.services.zip_service import extract_zip

router = APIRouter(prefix="/api/preflight", tags=["preflight"])
migration_router = APIRouter(prefix="/api/migration", tags=["migration"])


# =========================================================================
# POST /api/preflight/upload
# =========================================================================
@router.post("/upload", response_model=PreflightResult)
async def upload_zip(file: UploadFile = File(...)):
    """
    Accept a migration ZIP, run the full preflight validation pipeline, and
    return a structured result.
    """
    zip_bytes = await file.read()
    original_name = file.filename or "upload.zip"

    all_problems: list[Problem] = []

    # ---- Stage 1: ZIP Extraction ----
    run_id, dirs, zip_problems = extract_zip(zip_bytes, original_name)
    all_problems.extend(zip_problems)

    if _has_errors(zip_problems):
        return _build_result(run_id, all_problems, stage="zip_extraction", dirs=dirs)

    # ---- Stage 2: File Discovery ----
    yaml_path, conf_path, disc_problems = discover_files(dirs["extracted"])
    all_problems.extend(disc_problems)

    if _has_errors(disc_problems):
        return _build_result(run_id, all_problems, stage="file_discovery", dirs=dirs)

    assert yaml_path is not None
    assert conf_path is not None

    yaml_name = yaml_path.name
    conf_name = conf_path.name

    # ---- Stage 3: YAML Parsing ----
    yaml_data, yaml_jobs, yaml_problems = parse_yaml(yaml_path)
    all_problems.extend(yaml_problems)

    if _has_errors(yaml_problems):
        return _build_result(
            run_id, all_problems, stage="yaml_validation",
            dirs=dirs, yaml_file=yaml_name, conf_file=conf_name,
        )

    # ---- Stage 4: SeaTunnel Parsing ----
    raw_conf, st_jobs, conf_problems = parse_seatunnel(conf_path)
    all_problems.extend(conf_problems)

    if _has_errors(conf_problems):
        return _build_result(
            run_id, all_problems, stage="conf_validation",
            dirs=dirs, yaml_file=yaml_name, conf_file=conf_name,
        )

    # ---- Stage 5: Contract Validation ----
    contract_problems = validate_contract(yaml_data, yaml_jobs, yaml_name)
    all_problems.extend(contract_problems)

    # ---- Stage 6: Cross-Validation ----
    if yaml_jobs and st_jobs:
        cross_problems = cross_validate(yaml_jobs, st_jobs, yaml_name, conf_name)
        all_problems.extend(cross_problems)
    elif not yaml_jobs:
        all_problems.append(Problem(
            type="NO_YAML_JOBS",
            severity=Severity.WARNING,
            message="Validation contract declares zero active jobs — nothing to cross-validate.",
            file_a=yaml_name,
            stage="cross_validation",
        ))

    # ---- Stage 7: Build result & DVT Generation ----
    result = _build_result(
        run_id, all_problems, stage="preflight",
        dirs=dirs, yaml_file=yaml_name, conf_file=conf_name, jobs=yaml_jobs
    )
    return result


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
# GET /api/migration/{run_id}/status
# =========================================================================
@migration_router.get("/{run_id}/status")
async def get_migration_status(run_id: str):
    """Retrieve overall migration pipeline state (preflight, migration, dvt)."""
    return get_pipeline_state(run_id)


# =========================================================================
# POST /api/migration/{run_id}/mark-migrated
# =========================================================================
@migration_router.post("/{run_id}/mark-migrated")
async def mark_migration_complete(run_id: str, success: bool = True, details: str = "SeaTunnel execution completed"):
    """
    Mark SeaTunnel migration execution state for a run ID.
    Called by teammate's pipeline runner upon SeaTunnel completion.
    """
    state_str = "MIGRATION_SUCCESS" if success else "MIGRATION_FAILED"
    updated = save_pipeline_state(run_id, {
        "migration": state_str,
        "migration_message": details,
    })
    return {
        "run_id": run_id,
        "migration_status": state_str,
        "can_execute_dvt": updated.get("can_execute_dvt", False),
        "message": f"Migration state set to '{state_str}'.",
    }


# =========================================================================
# POST /api/migration/{run_id}/validate (Stage 3 DVT Execution)
# =========================================================================
@migration_router.post("/{run_id}/validate")
async def run_dvt_validation(run_id: str):
    """
    Start Stage 3 DVT Validation for a migrated package.

    Requires Stage 1 preflight success & Stage 2 SeaTunnel migration success.
    """
    result = execute_dvt_validation(run_id)
    return result


# =========================================================================
# GET /api/migration/{run_id}/validation
# =========================================================================
@migration_router.get("/{run_id}/validation")
async def get_dvt_validation_result(run_id: str):
    """Retrieve Stage 3 DVT validation result JSON."""
    dvt_result_path = RUNS_DIR / run_id / "dvt" / "result.json"
    if not dvt_result_path.exists():
        raise HTTPException(status_code=404, detail=f"DVT result for run '{run_id}' not found. Run validation first.")
    return json.loads(dvt_result_path.read_text(encoding="utf-8"))


# =========================================================================
# GET /api/migration/{run_id}/validation/report
# =========================================================================
@migration_router.get("/{run_id}/validation/report", response_class=PlainTextResponse)
async def get_dvt_validation_report(run_id: str):
    """Retrieve Stage 3 DVT Markdown validation report."""
    report_path = RUNS_DIR / run_id / "dvt" / "report.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"DVT report for run '{run_id}' not found.")
    return report_path.read_text(encoding="utf-8")


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
# GET /api/preflight/{run_id}/zip
# =========================================================================
@router.get("/{run_id}/zip", response_class=FileResponse)
async def get_uploaded_zip(run_id: str):
    """Download the original uploaded ZIP file for a given run ID."""
    uploaded_dir = RUNS_DIR / run_id / "uploaded"
    if not uploaded_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    zip_files = list(uploaded_dir.glob("*.zip"))
    if not zip_files:
        raise HTTPException(status_code=404, detail=f"ZIP file for run '{run_id}' not found.")
    target_zip = zip_files[0]
    return FileResponse(
        path=target_zip,
        media_type="application/zip",
        filename=target_zip.name,
    )


# =========================================================================
# GET /api/preflight/{run_id}/dvt-manifest
# =========================================================================
@router.get("/{run_id}/dvt-manifest")
async def get_dvt_manifest(run_id: str):
    """Retrieve the generated DVT validation manifest JSON."""
    manifest_path = RUNS_DIR / run_id / "generated" / "validation_manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"DVT manifest for run '{run_id}' not found.")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


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
    jobs: list[JobEntity] | None = None,
) -> PreflightResult:
    """Build the final PreflightResult from accumulated problems."""
    errors = [p for p in problems if p.severity == Severity.ERROR]
    warnings = [p for p in problems if p.severity == Severity.WARNING]

    failed_count = len(errors)
    warning_count = len(warnings)

    contract_checks = 0
    if jobs:
        for j in jobs:
            if j.checks:
                contract_checks += len(j.checks)

    if contract_checks > 0:
        total = contract_checks
    else:
        total = max(1, len(problems))

    passed_count = max(0, total - failed_count - warning_count)

    if errors:
        status = OverallStatus.BLOCKED
        can_execute = False
        msg = "Preflight validation failed. Fix the reported mismatches before migration."
    elif warnings:
        status = OverallStatus.REVIEW
        can_execute = False
        msg = "Preflight validation completed with warnings requiring review before migration."
    else:
        status = OverallStatus.READY
        can_execute = True
        msg = "Preflight validation successful. YAML and SeaTunnel configuration are consistent."

    result = PreflightResult(
        run_id=run_id,
        status=status,
        can_execute_seatunnel=can_execute,
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
        generated_dir = dirs.get("generated", RUNS_DIR / run_id / "generated")

        reports_dir.mkdir(parents=True, exist_ok=True)
        generated_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON result
        result_path = reports_dir / "preflight_result.json"
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        # Generate Markdown report
        generate_report(result, reports_dir)

        # Generate DVT Manifest & Config in runs/<run_id>/generated/
        if jobs:
            generate_dvt_manifest(run_id, jobs, status, generated_dir)

        # Update pipeline state
        save_pipeline_state(run_id, {
            "preflight": status.value,
            "preflight_message": msg,
        })

    return result
