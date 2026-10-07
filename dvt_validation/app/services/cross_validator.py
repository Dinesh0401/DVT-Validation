"""
Cross-Validator — the heart of Stage 1.

Compares the YAML validation contract against the SeaTunnel .conf to verify
they are consistent.  Every comparison is dynamic: entity names, columns,
tables, SQL, and mappings come from the uploaded files.
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
    if not sql:
        return ""
    s = sql.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    s = s.rstrip(";").strip()
    return s


def _extract_select_columns_normalised(sql: str | None) -> list[str]:
    if not sql:
        return []
    norm = _normalise_sql(sql)
    m = re.search(r"\bselect\s+(.*?)\s+\bfrom\b", norm, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    select_body = m.group(1)
    aliases = re.findall(r'\bas\s+"?([a-zA-Z0-9_]+)"?', select_body, re.IGNORECASE)
    if aliases:
        return [a.lower() for a in aliases]
    return []


def _extract_from_table_normalised(sql: str | None) -> tuple[str, str]:
    if not sql:
        return ("", "")
    norm = _normalise_sql(sql)
    m = re.search(r'from\s+["`]?([a-zA-Z0-9_]+)["`]?\s*\.\s*["`]?([a-zA-Z0-9_]+)["`]', norm, re.IGNORECASE)
    if m:
        return (m.group(1).lower(), m.group(2).lower())
    m2 = re.search(r'from\s+["`]?([a-zA-Z0-9_]+)["`]', norm, re.IGNORECASE)
    if m2:
        return ("", m2.group(1).lower())
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
            if sj.job_id == yj.job_id or sj.job_id.removeprefix("ST:") == yj.job_id:
                matched.append((yj, sj))
                used_st.add(idx)
                found = True
                break
        if found:
            continue

        # Strategy 2: source table match (with or without schema)
        y_src_tbl = (yj.source.table_name or "").lower()
        y_src_sch = (yj.source.schema_name or "").lower()
        if y_src_tbl:
            for idx, sj in enumerate(st_jobs):
                if idx in used_st:
                    continue
                s_src_tbl = (sj.source.table_name or "").lower()
                s_src_sch = (sj.source.schema_name or "").lower()

                if y_src_tbl == s_src_tbl:
                    if not y_src_sch or not s_src_sch or y_src_sch == s_src_sch:
                        matched.append((yj, sj))
                        used_st.add(idx)
                        found = True
                        break
        if found:
            continue

        # Strategy 3: target table match (with or without schema)
        y_tgt_tbl = (yj.target.table_name or "").lower()
        y_tgt_sch = (yj.target.schema_name or "").lower()
        if y_tgt_tbl:
            for idx, sj in enumerate(st_jobs):
                if idx in used_st:
                    continue
                s_tgt_tbl = (sj.target.table_name or "").lower()
                s_tgt_sch = (sj.target.schema_name or "").lower()

                if y_tgt_tbl == s_tgt_tbl:
                    if not y_tgt_sch or not s_tgt_sch or y_tgt_sch == s_tgt_sch:
                        matched.append((yj, sj))
                        used_st.add(idx)
                        found = True
                        break
        if found:
            continue

        unmatched_yaml.append(yj)

    # Strategy 4: Fallback for single-job packages
    if len(unmatched_yaml) == 1 and (len(st_jobs) - len(used_st)) == 1:
        yj = unmatched_yaml.pop(0)
        st_idx = next(i for i in range(len(st_jobs)) if i not in used_st)
        sj = st_jobs[st_idx]
        matched.append((yj, sj))
        used_st.add(st_idx)

    # Report remaining unmatched YAML jobs
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

    # Report remaining unmatched SeaTunnel jobs
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
            path_b="source.query",
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
            path_b="source.query",
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
            path_b="sink.table",
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
            path_b="sink.table",
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
            path_a=f"job.{job_id}.source.columns",
            file_b=conf_file,
            path_b="source.query",
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
            path_a="source.query",
            file_b=yaml_file,
            path_b=f"job.{job_id}.source.columns",
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
            message="Column order differs between contract and SeaTunnel.",
            file_a=yaml_file,
            path_a=f"job.{job_id}.source.columns",
            file_b=conf_file,
            path_b="source.query",
            expected=yj.source.columns,
            actual=sj.source.columns,
            job=job_id,
            stage="cross_validation",
        ))

    # ---- 5. Snapshot / SCN binding ----
    if yj.snapshot_required:
        if not sj.snapshot_binding:
            problems.append(Problem(
                type="MISSING_SCN_IN_SEATUNNEL",
                severity=Severity.ERROR,
                message="Contract requires snapshot (SCN) but SeaTunnel source query does not contain 'AS OF SCN'.",
                file_a=yaml_file,
                path_a=f"job.{job_id}.snapshot",
                file_b=conf_file,
                path_b="source.query",
                expected="AS OF SCN binding",
                actual="not found",
                job=job_id,
                stage="cross_validation",
            ))

    # ---- 6. Transform consistency ----
    for t in sj.transforms:
        if t.source_table and t.result_table:
            problems.append(Problem(
                type="TRANSFORM_CHAIN_INFO",
                severity=Severity.INFO,
                message=f"SeaTunnel transform: {t.source_table} → {t.result_table} (query: {t.query or 'N/A'}).",
                file_b=conf_file,
                path_b="transform.SQL",
                job=job_id,
                stage="cross_validation",
            ))

    return problems


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cross_validate(
    yaml_jobs: list[JobEntity],
    st_jobs: list[JobEntity],
    yaml_file: str,
    conf_file: str,
) -> list[Problem]:
    all_problems: list[Problem] = []
    matched, match_problems = _match_jobs(yaml_jobs, st_jobs, yaml_file, conf_file)
    all_problems.extend(match_problems)

    for yj, sj in matched:
        pair_problems = _cross_check_pair(yj, sj, yaml_file, conf_file)
        all_problems.extend(pair_problems)

    return all_problems
