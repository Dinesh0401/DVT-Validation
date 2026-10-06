"""
YAML Parser — parse and structurally validate the validation contract YAML.

Everything is dynamic: the parser reads whatever jobs, columns, tables,
checks, and schemas the YAML declares and normalises them into ``JobEntity``
objects for downstream comparison.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from app.models.preflight_models import (
    JobEntity,
    Problem,
    Severity,
    SourceEntity,
    TargetEntity,
    TransformEntity,
)


# ---------------------------------------------------------------------------
# Column extraction from SQL strings
# ---------------------------------------------------------------------------
_SELECT_COL_RE = re.compile(
    r"""
    (?:AS\s+)?              # optional AS keyword
    "([^"]+)"               # quoted identifier
    """,
    re.IGNORECASE | re.VERBOSE,
)

_ALIAS_RE = re.compile(
    r"""\bAS\s+"([^"]+)"\s*""",
    re.IGNORECASE,
)


def _extract_alias_columns(sql: str | None) -> list[str]:
    """
    Extract the **target alias** column names from a SELECT projection.

    For ``SELECT "FOO" AS "bar", "BAZ" AS "qux" FROM …``
    returns ``["bar", "qux"]``.
    """
    if not sql:
        return []
    # Only look at the SELECT clause (before FROM)
    upper = sql.upper()
    from_idx = _find_top_level_from(upper)
    select_clause = sql[:from_idx] if from_idx > 0 else sql
    return [m.group(1) for m in _ALIAS_RE.finditer(select_clause)]


def _find_top_level_from(sql_upper: str) -> int:
    """Find the position of the top-level FROM keyword (not inside subqueries)."""
    depth = 0
    i = 0
    while i < len(sql_upper):
        ch = sql_upper[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and sql_upper[i:i + 5] == "FROM " or sql_upper[i:i + 5] == "FROM\n":
            return i
        i += 1
    return -1


def _extract_source_relation(sql: str | None) -> tuple[str | None, str | None]:
    """
    Extract schema.table from a FROM clause like ``FROM "HR"."EMPLOYEES" …``
    Returns (schema, table) or (None, None).
    """
    if not sql:
        return None, None
    m = re.search(r'FROM\s+"([^"]+)"\s*\.\s*"([^"]+)"', sql, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _has_scn_binding(sql: str | None) -> bool:
    """Check if the SQL contains an SCN / snapshot binding."""
    if not sql:
        return False
    return bool(re.search(r'AS\s+OF\s+SCN\s+\$\{?\w+\}?', sql, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_yaml(yaml_path: Path) -> tuple[dict[str, Any], list[JobEntity], list[Problem]]:
    """
    Parse the YAML validation contract and return
    ``(raw_data, jobs_list, problems)``.
    """
    problems: list[Problem] = []
    fname = yaml_path.name

    # ---- Parse ----
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        problems.append(Problem(
            type="YAML_SYNTAX_ERROR",
            severity=Severity.ERROR,
            message=f"YAML syntax error: {exc}",
            file_a=fname,
            stage="yaml_validation",
        ))
        return {}, [], problems

    if not isinstance(data, dict):
        problems.append(Problem(
            type="YAML_STRUCTURE_ERROR",
            severity=Severity.ERROR,
            message="YAML root must be a mapping (dict), got " + type(data).__name__,
            file_a=fname,
            stage="yaml_validation",
        ))
        return {}, [], problems

    # ---- Required top-level sections ----
    required_sections = {"engine", "job"}
    for sec in required_sections:
        if sec not in data:
            problems.append(Problem(
                type="MISSING_SECTION",
                severity=Severity.ERROR,
                message=f"Required top-level section '{sec}' is missing.",
                file_a=fname,
                path_a=sec,
                stage="yaml_validation",
            ))

    # ---- Validate acquisition ----
    acquisition = data.get("acquisition")
    snapshot_required = acquisition == "snapshot"

    # ---- Validate bindings ----
    bindings = data.get("bindings", {})
    snapshot_binding = None
    if snapshot_required and isinstance(bindings, dict):
        snapshot_binding = bindings.get("run_scn")

    # ---- Parse jobs ----
    jobs_section = data.get("job", {})
    if not isinstance(jobs_section, dict):
        problems.append(Problem(
            type="YAML_STRUCTURE_ERROR",
            severity=Severity.ERROR,
            message="'job' section must be a mapping, got " + type(jobs_section).__name__,
            file_a=fname,
            path_a="job",
            stage="yaml_validation",
        ))
        return data, [], problems

    jobs: list[JobEntity] = []
    seen_job_ids: set[str] = set()

    for job_id, job_data in jobs_section.items():
        # ---- Duplicate job check ----
        if job_id in seen_job_ids:
            problems.append(Problem(
                type="DUPLICATE_JOB",
                severity=Severity.ERROR,
                message=f"Job '{job_id}' is declared more than once.",
                file_a=fname,
                path_a=f"job.{job_id}",
                stage="yaml_validation",
                job=job_id,
            ))
            continue
        seen_job_ids.add(job_id)

        if not isinstance(job_data, dict):
            problems.append(Problem(
                type="YAML_STRUCTURE_ERROR",
                severity=Severity.ERROR,
                message=f"Job '{job_id}' must be a mapping.",
                file_a=fname,
                path_a=f"job.{job_id}",
                stage="yaml_validation",
                job=job_id,
            ))
            continue

        # ---- Source ----
        src_data = job_data.get("source", {})
        projection_sql = src_data.get("projection") if isinstance(src_data, dict) else None
        src_schema, src_table = _extract_source_relation(projection_sql)
        src_columns = _extract_alias_columns(projection_sql)
        src_has_scn = _has_scn_binding(projection_sql)

        source = SourceEntity(
            schema_name=src_schema,
            table_name=src_table,
            relation=src_data.get("projection_view") if isinstance(src_data, dict) else None,
            columns=src_columns,
            projection_sql=projection_sql,
            snapshot_binding="${run_scn}" if src_has_scn else None,
        )

        # Raw relations
        raw_rels = src_data.get("raw_relations", []) if isinstance(src_data, dict) else []
        if isinstance(raw_rels, list):
            for rr in raw_rels:
                if isinstance(rr, dict):
                    if not source.schema_name and rr.get("schema"):
                        source.schema_name = rr["schema"]
                    if not source.table_name and rr.get("table"):
                        source.table_name = rr["table"]

        # ---- Target ----
        tgt_data = job_data.get("target", {})
        tgt_relation = tgt_data.get("relation", "") if isinstance(tgt_data, dict) else ""
        tgt_schema, tgt_table = None, None
        if isinstance(tgt_relation, str):
            m = re.match(r'"([^"]+)"\s*\.\s*"([^"]+)"', tgt_relation)
            if m:
                tgt_schema = m.group(1)
                tgt_table = m.group(2)

        target = TargetEntity(
            schema_name=tgt_schema,
            table_name=tgt_table,
            relation=tgt_data.get("view") if isinstance(tgt_data, dict) else None,
            columns=src_columns,  # contract: target receives the same columns
        )

        # ---- Validate source ----
        if not source.columns and not isinstance(jobs_section.get(job_id), dict):
            problems.append(Problem(
                type="MISSING_SOURCE_COLUMNS",
                severity=Severity.ERROR,
                message=f"Job '{job_id}' source has no identifiable columns.",
                file_a=fname,
                path_a=f"job.{job_id}.source",
                stage="yaml_validation",
                job=job_id,
            ))

        # ---- Validate target ----
        if not tgt_schema and not tgt_table:
            if isinstance(tgt_data, dict) and tgt_data:
                problems.append(Problem(
                    type="MISSING_TARGET_DEFINITION",
                    severity=Severity.WARNING,
                    message=f"Job '{job_id}' target relation could not be parsed.",
                    file_a=fname,
                    path_a=f"job.{job_id}.target",
                    stage="yaml_validation",
                    job=job_id,
                ))

        # ---- Checks ----
        checks_data = job_data.get("check", [])
        checks_list = checks_data if isinstance(checks_data, list) else []

        seen_check_ids: set[str] = set()
        for idx, chk in enumerate(checks_list):
            if not isinstance(chk, dict):
                continue
            cid = chk.get("check_id", "")
            if cid in seen_check_ids:
                problems.append(Problem(
                    type="DUPLICATE_CHECK",
                    severity=Severity.ERROR,
                    message=f"Check '{cid}' is declared more than once in job '{job_id}'.",
                    file_a=fname,
                    path_a=f"job.{job_id}.check[{idx}]",
                    stage="yaml_validation",
                    job=job_id,
                ))
            seen_check_ids.add(cid)

        # ---- Column duplicates ----
        if src_columns:
            col_lower = [c.lower() for c in src_columns]
            seen_cols: set[str] = set()
            for i, c in enumerate(col_lower):
                if c in seen_cols:
                    problems.append(Problem(
                        type="DUPLICATE_COLUMN",
                        severity=Severity.ERROR,
                        message=f"Column '{src_columns[i]}' is declared more than once in job '{job_id}' source projection.",
                        file_a=fname,
                        path_a=f"job.{job_id}.source.projection",
                        stage="yaml_validation",
                        job=job_id,
                    ))
                seen_cols.add(c)

        # ---- Build entity ----
        job_entity = JobEntity(
            job_id=job_id,
            source=source,
            target=target,
            columns=src_columns,
            checks=[c for c in checks_list if isinstance(c, dict)],
            snapshot_required=snapshot_required,
            snapshot_binding=snapshot_binding,
            raw_data=job_data,
        )
        jobs.append(job_entity)

    # ---- Summary consistency ----
    summary = data.get("summary", {})
    if isinstance(summary, dict):
        declared_jobs = summary.get("jobs")
        if declared_jobs is not None and isinstance(declared_jobs, int):
            actual_jobs = len(jobs)
            if declared_jobs != actual_jobs:
                problems.append(Problem(
                    type="SUMMARY_MISMATCH",
                    severity=Severity.WARNING,
                    message=f"Summary declares {declared_jobs} job(s) but {actual_jobs} were found.",
                    file_a=fname,
                    path_a="summary.jobs",
                    expected=declared_jobs,
                    actual=actual_jobs,
                    stage="yaml_validation",
                ))

    return data, jobs, problems
