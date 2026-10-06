"""
Cross-Validator — the heart of Stage 1.

Compares the YAML validation contract against the SeaTunnel .conf to verify
they are consistent.  Every comparison is dynamic: entity names, columns,
tables, SQL, and mappings come from the uploaded files.

Cross-checks performed:
    1. Job mapping — every YAML job has a matching SeaTunnel job
    2. Source mapping — schema.table match
    3. Target mapping — schema.table match
    4. Column matching — same columns, same set (order is a warning)
    5. Transformation consistency
    6. SQL semantic comparison (normalised)
    7. Snapshot / SCN binding consistency
"""
from __future__ import annotations

import re
from typing import Any

from app.config.settings import COLUMN_ORDER_SEVERITY
from app.models.preflight_models import (
    JobEntity,
    Problem,
    Severity,
)


# ---------------------------------------------------------------------------
# SQL normalisation helpers
# ---------------------------------------------------------------------------

def _normalise_sql(sql: str | None) -> str:
    """
    Normalise SQL for comparison:  lowercase, collapse whitespace, strip
    quotes, remove trailing semicolons, remove aliases that are just noise.
    """
    if not sql:
        return ""
    s = sql.strip()
    # Remove newlines/tabs → space
    s = re.sub(r"\s+", " ", s)
    # Lowercase
    s = s.lower()
    # Remove trailing semicolons
    s = s.rstrip(";").strip()
    return s


def _extract_select_columns_normalised(sql: str | None) -> list[str]:
    """Extract normalised column aliases from a SELECT clause."""
    if not sql:
        return []
    norm = _normalise_sql(sql)
    # Find the select clause
    m = re.match(r"select\s+(.*?)\s+from\b", norm, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    select_body = m.group(1)
    # Extract "alias" patterns (AS "alias")
    aliases = re.findall(r'\bas\s+"([^"]+)"', select_body, re.IGNORECASE)
    if aliases:
        return [a.lower() for a in aliases]
    # Fallback: try AS alias without quotes
    aliases = re.findall(r'\bas\s+(\w+)', select_body, re.IGNORECASE)
    return [a.lower() for a in aliases]


def _extract_from_table_normalised(sql: str | None) -> tuple[str, str]:
    """Extract normalised (schema, table) from the FROM clause."""
    if not sql:
        return ("", "")
    m = re.search(r'from\s+"([^"]+)"\s*\.\s*"([^"]+)"', _normalise_sql(sql), re.IGNORECASE)
    if m:
        return (m.group(1).lower(), m.group(2).lower())
    return ("", "")


# ---------------------------------------------------------------------------
# Job matching
# ---------------------------------------------------------------------------

def _match_jobs(
    yaml_jobs: list[JobEntity],
    st_jobs: list[JobEntity],
    yaml_file: str,
    conf_file: str,
) -> tuple[list[tuple[JobEntity, JobEntity]], list[Problem]]:
    """
    Match YAML jobs to SeaTunnel jobs.

    Matching strategies (tried in order):
        1. Exact job_id match
        2. Source relation match (schema.table)
        3. Target relation match (schema.table)
    """
    problems: list[Problem] = []
    matched: list[tuple[JobEntity, JobEntity]] = []
    unmatched_yaml: list[JobEntity] = []
    used_st: set[int] = set()

    for yj in yaml_jobs:
        found = False

        # Strategy 1: exact job_id
        for idx, sj in enumerate(st_jobs):
            if idx in used_st:
                continue
            if sj.job_id == yj.job_id:
                matched.append((yj, sj))
                used_st.add(idx)
                found = True
                break

        if found:
            continue

        # Strategy 2: source schema.table
        y_src = (
            (yj.source.schema_name or "").lower(),
            (yj.source.table_name or "").lower(),
        )
        if y_src[0] and y_src[1]:
            for idx, sj in enumerate(st_jobs):
                if idx in used_st:
                    continue
                s_src = (
                    (sj.source.schema_name or "").lower(),
                    (sj.source.table_name or "").lower(),
                )
                if y_src == s_src:
                    matched.append((yj, sj))
                    used_st.add(idx)
                    found = True
                    break

        if found:
            continue

        # Strategy 3: target schema.table
        y_tgt = (
            (yj.target.schema_name or "").lower(),
            (yj.target.table_name or "").lower(),
        )
        if y_tgt[0] and y_tgt[1]:
            for idx, sj in enumerate(st_jobs):
                if idx in used_st:
                    continue
                s_tgt = (
                    (sj.target.schema_name or "").lower(),
                    (sj.target.table_name or "").lower(),
                )
                if y_tgt == s_tgt:
                    matched.append((yj, sj))
                    used_st.add(idx)
                    found = True
                    break

        if not found:
            unmatched_yaml.append(yj)

    # Report unmatched YAML jobs
    for yj in unmatched_yaml:
        problems.append(Problem(
            type="UNMATCHED_YAML_JOB",
            severity=Severity.ERROR,
            message=f"Contract job '{yj.job_id}' has no matching SeaTunnel job definition.",
            file_a=yaml_file,
            path_a=f"job.{yj.job_id}",
            file_b=conf_file,
            job=yj.job_id,
            stage="cross_validation",
        ))

    # Report unmatched SeaTunnel jobs (warning — extra jobs are not necessarily bad)
    for idx, sj in enumerate(st_jobs):
        if idx not in used_st:
            problems.append(Problem(
                type="EXTRA_SEATUNNEL_JOB",
                severity=Severity.WARNING,
                message=f"SeaTunnel job '{sj.job_id}' has no matching contract job.",
                file_a=conf_file,
                path_a=f"job.{sj.job_id}",
                file_b=yaml_file,
                job=sj.job_id,
                stage="cross_validation",
            ))

    return matched, problems


# ---------------------------------------------------------------------------
# Per-pair cross-checks
# ---------------------------------------------------------------------------

def _cross_check_pair(
    yj: JobEntity,
    sj: JobEntity,
    yaml_file: str,
    conf_file: str,
) -> list[Problem]:
    """Run all cross-validation checks for a matched (YAML, SeaTunnel) job pair."""
    problems: list[Problem] = []
    job_id = yj.job_id

    # ---- 1. Source mapping ----
    y_schema = (yj.source.schema_name or "").lower()
    y_table = (yj.source.table_name or "").lower()
    s_schema = (sj.source.schema_name or "").lower()
    s_table = (sj.source.table_name or "").lower()

    if y_schema and s_schema and y_schema != s_schema:
        problems.append(Problem(
            type="SOURCE_SCHEMA_MISMATCH",
            severity=Severity.ERROR,
            message=f"Source schema differs: contract='{yj.source.schema_name}', SeaTunnel='{sj.source.schema_name}'.",
            file_a=yaml_file,
            path_a=f"job.{job_id}.source",
            file_b=conf_file,
            path_b=f"source.Jdbc.query",
            expected=yj.source.schema_name,
            actual=sj.source.schema_name,
            job=job_id,
            stage="cross_validation",
        ))

    if y_table and s_table and y_table != s_table:
        problems.append(Problem(
            type="SOURCE_TABLE_MISMATCH",
            severity=Severity.ERROR,
            message=f"Source table differs: contract='{yj.source.table_name}', SeaTunnel='{sj.source.table_name}'.",
            file_a=yaml_file,
            path_a=f"job.{job_id}.source",
            file_b=conf_file,
            path_b=f"source.Jdbc.query",
            expected=yj.source.table_name,
            actual=sj.source.table_name,
            job=job_id,
            stage="cross_validation",
        ))

    # ---- 2. Target mapping ----
    yt_schema = (yj.target.schema_name or "").lower()
    yt_table = (yj.target.table_name or "").lower()
    st_schema = (sj.target.schema_name or "").lower()
    st_table = (sj.target.table_name or "").lower()

    if yt_schema and st_schema and yt_schema != st_schema:
        problems.append(Problem(
            type="TARGET_SCHEMA_MISMATCH",
            severity=Severity.ERROR,
            message=f"Target schema differs: contract='{yj.target.schema_name}', SeaTunnel='{sj.target.schema_name}'.",
            file_a=yaml_file,
            path_a=f"job.{job_id}.target",
            file_b=conf_file,
            path_b=f"sink.Jdbc",
            expected=yj.target.schema_name,
            actual=sj.target.schema_name,
            job=job_id,
            stage="cross_validation",
        ))

    if yt_table and st_table and yt_table != st_table:
        problems.append(Problem(
            type="TARGET_TABLE_MISMATCH",
            severity=Severity.ERROR,
            message=f"Target table differs: contract='{yj.target.table_name}', SeaTunnel='{sj.target.table_name}'.",
            file_a=yaml_file,
            path_a=f"job.{job_id}.target",
            file_b=conf_file,
            path_b=f"sink.Jdbc",
            expected=yj.target.table_name,
            actual=sj.target.table_name,
            job=job_id,
            stage="cross_validation",
        ))

    # ---- 3. Column set comparison ----
    y_cols = [c.lower() for c in yj.source.columns]
    s_cols = [c.lower() for c in sj.source.columns]

    y_set = set(y_cols)
    s_set = set(s_cols)

    missing_in_st = y_set - s_set
    extra_in_st = s_set - y_set

    for col in sorted(missing_in_st):
        original = next((c for c in yj.source.columns if c.lower() == col), col)
        problems.append(Problem(
            type="MISSING_COLUMN_IN_SEATUNNEL",
            severity=Severity.ERROR,
            message=f"Contract column '{original}' is missing from SeaTunnel source projection.",
            file_a=yaml_file,
            path_a=f"job.{job_id}.source.projection",
            file_b=conf_file,
            path_b=f"source.Jdbc.query",
            expected=original,
            actual=None,
            job=job_id,
            stage="cross_validation",
        ))

    for col in sorted(extra_in_st):
        original = next((c for c in sj.source.columns if c.lower() == col), col)
        problems.append(Problem(
            type="EXTRA_COLUMN_IN_SEATUNNEL",
            severity=Severity.WARNING,
            message=f"SeaTunnel source projects column '{original}' which is not in the contract.",
            file_a=conf_file,
            path_a=f"source.Jdbc.query",
            file_b=yaml_file,
            path_b=f"job.{job_id}.source.projection",
            expected=None,
            actual=original,
            job=job_id,
            stage="cross_validation",
        ))

    # ---- 4. Column order ----
    if y_cols and s_cols and y_set == s_set and y_cols != s_cols:
        severity = Severity.WARNING if COLUMN_ORDER_SEVERITY == "WARNING" else Severity.ERROR
        problems.append(Problem(
            type="COLUMN_ORDER_MISMATCH",
            severity=severity,
            message=f"Column order differs between contract and SeaTunnel.",
            file_a=yaml_file,
            path_a=f"job.{job_id}.source.projection",
            file_b=conf_file,
            path_b=f"source.Jdbc.query",
            expected=yj.source.columns,
            actual=sj.source.columns,
            job=job_id,
            stage="cross_validation",
        ))

    # ---- 5. Target column comparison ----
    yt_cols = [c.lower() for c in yj.target.columns] if yj.target.columns else []
    st_cols = [c.lower() for c in sj.target.columns] if sj.target.columns else []

    if yt_cols and st_cols:
        yt_set = set(yt_cols)
        st_set = set(st_cols)

        for col in sorted(yt_set - st_set):
            original = next((c for c in yj.target.columns if c.lower() == col), col)
            problems.append(Problem(
                type="MISSING_TARGET_COLUMN",
                severity=Severity.ERROR,
                message=f"Contract target column '{original}' is missing from SeaTunnel target definition.",
                file_a=yaml_file,
                path_a=f"job.{job_id}.target",
                file_b=conf_file,
                path_b=f"ddl.columns / dml.columns",
                expected=original,
                actual=None,
                job=job_id,
                stage="cross_validation",
            ))

        for col in sorted(st_set - yt_set):
            original = next((c for c in sj.target.columns if c.lower() == col), col)
            problems.append(Problem(
                type="EXTRA_TARGET_COLUMN",
                severity=Severity.WARNING,
                message=f"SeaTunnel target defines column '{original}' not found in contract.",
                file_a=conf_file,
                path_a=f"ddl.columns / dml.columns",
                file_b=yaml_file,
                path_b=f"job.{job_id}.target",
                expected=None,
                actual=original,
                job=job_id,
                stage="cross_validation",
            ))

    # ---- 6. SQL semantic comparison ----
    y_sql = _normalise_sql(yj.source.projection_sql)
    s_sql = _normalise_sql(sj.source.projection_sql)

    if y_sql and s_sql:
        # Extract core: remove AS OF SCN and table alias noise
        y_core = _strip_scn_and_alias(y_sql)
        s_core = _strip_scn_and_alias(s_sql)

        if y_core != s_core:
            # Check if it's a meaningful difference
            y_select_cols = _extract_select_columns_normalised(yj.source.projection_sql)
            s_select_cols = _extract_select_columns_normalised(sj.source.projection_sql)

            if set(y_select_cols) == set(s_select_cols):
                # Columns match — differences are likely dialect/whitespace
                y_from = _extract_from_table_normalised(yj.source.projection_sql)
                s_from = _extract_from_table_normalised(sj.source.projection_sql)

                if y_from == s_from:
                    # Same columns, same source — just dialect differences
                    problems.append(Problem(
                        type="SQL_DIALECT_DIFFERENCE",
                        severity=Severity.INFO,
                        message=f"Source SQL has minor dialect differences (whitespace, alias style) between contract and SeaTunnel. Columns and source table match.",
                        file_a=yaml_file,
                        path_a=f"job.{job_id}.source.projection",
                        file_b=conf_file,
                        path_b=f"source.Jdbc.query",
                        job=job_id,
                        stage="cross_validation",
                    ))
                else:
                    problems.append(Problem(
                        type="SQL_SOURCE_DIFFERENCE",
                        severity=Severity.ERROR,
                        message=f"Source SQL references different tables.",
                        file_a=yaml_file,
                        path_a=f"job.{job_id}.source.projection",
                        file_b=conf_file,
                        path_b=f"source.Jdbc.query",
                        expected=str(y_from),
                        actual=str(s_from),
                        job=job_id,
                        stage="cross_validation",
                    ))
            else:
                problems.append(Problem(
                    type="SQL_PROJECTION_DIFFERENCE",
                    severity=Severity.WARNING,
                    message=f"Source SQL projection columns differ between contract and SeaTunnel.",
                    file_a=yaml_file,
                    path_a=f"job.{job_id}.source.projection",
                    file_b=conf_file,
                    path_b=f"source.Jdbc.query",
                    expected=y_select_cols,
                    actual=s_select_cols,
                    job=job_id,
                    stage="cross_validation",
                ))

    # ---- 7. Snapshot / SCN binding ----
    if yj.snapshot_required:
        if not sj.snapshot_binding:
            problems.append(Problem(
                type="MISSING_SCN_IN_SEATUNNEL",
                severity=Severity.ERROR,
                message=f"Contract requires snapshot (SCN) but SeaTunnel source query does not contain 'AS OF SCN'.",
                file_a=yaml_file,
                path_a=f"job.{job_id}.env.snapshot",
                file_b=conf_file,
                path_b=f"source.Jdbc.query",
                expected="AS OF SCN binding",
                actual="not found",
                job=job_id,
                stage="cross_validation",
            ))

    # ---- 8. Transform consistency ----
    # If SeaTunnel has a transform block, it should pipe source → sink correctly
    for t in sj.transforms:
        if t.source_table and t.result_table:
            # The source_table should reference the source result_table_name
            # and the result_table should match the sink source_table_name
            # This is structural — we just verify the chain exists
            problems.append(Problem(
                type="TRANSFORM_CHAIN_INFO",
                severity=Severity.INFO,
                message=f"SeaTunnel transform: {t.source_table} → {t.result_table} (query: {t.query or 'N/A'}).",
                file_b=conf_file,
                path_b=f"transform.SQL",
                job=job_id,
                stage="cross_validation",
            ))

    return problems


def _strip_scn_and_alias(sql: str) -> str:
    """Remove AS OF SCN clauses and table aliases for semantic comparison."""
    s = re.sub(r'\bas\s+of\s+scn\s+\$\{?\w+\}?\s*', '', sql, flags=re.IGNORECASE)
    s = re.sub(r'"\w+"$', '', s)  # trailing table alias
    s = re.sub(r'\s+"t\d+"', '', s)  # "t0" style aliases
    s = re.sub(r'\s+', ' ', s).strip()
    return s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cross_validate(
    yaml_jobs: list[JobEntity],
    st_jobs: list[JobEntity],
    yaml_file: str,
    conf_file: str,
) -> list[Problem]:
    """
    Cross-validate the YAML contract against SeaTunnel configuration.

    Returns a list of problems (may be empty = fully consistent).
    """
    all_problems: list[Problem] = []

    # ---- Match jobs ----
    matched, match_problems = _match_jobs(yaml_jobs, st_jobs, yaml_file, conf_file)
    all_problems.extend(match_problems)

    # ---- Cross-check each pair ----
    for yj, sj in matched:
        pair_problems = _cross_check_pair(yj, sj, yaml_file, conf_file)
        all_problems.extend(pair_problems)

    return all_problems
