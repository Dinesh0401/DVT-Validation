"""
Contract Validator — structural validation of the YAML contract in isolation.

Validates that the contract is internally consistent without comparing to
the SeaTunnel file.  All checks are dynamic.
"""
from __future__ import annotations

from app.models.preflight_models import JobEntity, Problem, Severity


def validate_contract(
    yaml_data: dict,
    yaml_jobs: list[JobEntity],
    yaml_filename: str,
) -> list[Problem]:
    """
    Validate the parsed YAML contract for internal consistency.

    Returns a list of problems (may be empty = all good).
    """
    problems: list[Problem] = []

    # ---- 1. Engine presence ----
    engine = yaml_data.get("engine", {})
    if not isinstance(engine, dict) or not engine.get("name"):
        problems.append(Problem(
            type="MISSING_ENGINE",
            severity=Severity.WARNING,
            message="Validation contract does not specify an engine name.",
            file_a=yaml_filename,
            path_a="engine.name",
            stage="contract_validation",
        ))

    # ---- 2. Convention presence ----
    convention = yaml_data.get("convention")
    if not isinstance(convention, dict):
        problems.append(Problem(
            type="MISSING_CONVENTION",
            severity=Severity.WARNING,
            message="Validation contract does not have a 'convention' section.",
            file_a=yaml_filename,
            path_a="convention",
            stage="contract_validation",
        ))

    # ---- 3. Acquisition ----
    acquisition = yaml_data.get("acquisition")
    if not acquisition:
        problems.append(Problem(
            type="MISSING_ACQUISITION",
            severity=Severity.WARNING,
            message="Validation contract does not specify an acquisition mode.",
            file_a=yaml_filename,
            path_a="acquisition",
            stage="contract_validation",
        ))

    # ---- 4. Per-job checks ----
    for job in yaml_jobs:
        prefix = f"job.{job.job_id}"

        # Source must have columns
        if not job.source.columns:
            problems.append(Problem(
                type="EMPTY_SOURCE_COLUMNS",
                severity=Severity.WARNING,
                message=f"Job '{job.job_id}' source projection has no identifiable columns.",
                file_a=yaml_filename,
                path_a=f"{prefix}.source.projection",
                stage="contract_validation",
                job=job.job_id,
            ))

        # Target relation should be parseable
        if not job.target.schema_name and not job.target.table_name:
            problems.append(Problem(
                type="UNPARSEABLE_TARGET",
                severity=Severity.WARNING,
                message=f"Job '{job.job_id}' target relation could not be fully parsed.",
                file_a=yaml_filename,
                path_a=f"{prefix}.target.relation",
                stage="contract_validation",
                job=job.job_id,
            ))

        # Snapshot consistency: if acquisition is snapshot, job env should bind it
        if job.snapshot_required:
            env = job.raw_data.get("env", {})
            snapshot_ref = env.get("snapshot", "") if isinstance(env, dict) else ""
            binds = env.get("binds", []) if isinstance(env, dict) else []
            if not snapshot_ref and "run_scn" not in binds:
                problems.append(Problem(
                    type="SNAPSHOT_NOT_BOUND",
                    severity=Severity.WARNING,
                    message=f"Job '{job.job_id}' does not bind the snapshot variable despite snapshot acquisition mode.",
                    file_a=yaml_filename,
                    path_a=f"{prefix}.env.snapshot",
                    stage="contract_validation",
                    job=job.job_id,
                ))

        # Checks should have unique IDs (already validated in parser, but double-check)
        check_ids = [c.get("check_id") for c in job.checks if isinstance(c, dict)]
        if len(check_ids) != len(set(check_ids)):
            problems.append(Problem(
                type="DUPLICATE_CHECK_IDS",
                severity=Severity.ERROR,
                message=f"Job '{job.job_id}' has duplicate check IDs.",
                file_a=yaml_filename,
                path_a=f"{prefix}.check",
                stage="contract_validation",
                job=job.job_id,
            ))

        # Every check with a SQL should have valid dialect info
        for idx, chk in enumerate(job.checks):
            if not isinstance(chk, dict):
                continue
            if chk.get("sql") and not chk.get("query_dialect"):
                problems.append(Problem(
                    type="MISSING_CHECK_DIALECT",
                    severity=Severity.INFO,
                    message=f"Check '{chk.get('check_id', idx)}' has SQL but no query_dialect.",
                    file_a=yaml_filename,
                    path_a=f"{prefix}.check[{idx}].query_dialect",
                    stage="contract_validation",
                    job=job.job_id,
                ))

    # ---- 5. Blocked jobs ----
    summary = yaml_data.get("summary", {})
    blocked = summary.get("blocked_jobs", []) if isinstance(summary, dict) else []
    if isinstance(blocked, list) and blocked:
        for bj in blocked:
            problems.append(Problem(
                type="BLOCKED_JOB",
                severity=Severity.WARNING,
                message=f"Job '{bj}' is blocked in the contract and will not be validated.",
                file_a=yaml_filename,
                path_a=f"summary.blocked_jobs",
                stage="contract_validation",
                job=str(bj),
            ))

    return problems
