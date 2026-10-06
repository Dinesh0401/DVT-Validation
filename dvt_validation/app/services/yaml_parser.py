"""
YAML Parser — parse and structurally validate the validation contract YAML.

Supports all dynamic contract variants:
- top-level 'job' or 'jobs' key (dict or list)
- direct 'table' / 'columns' fields or 'projection' SQL queries
- 'acquisition: snapshot' or explicit 'scn_snapshot' per job
- schema-level source / target metadata
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
)


# ---------------------------------------------------------------------------
# Column and table extraction helpers
# ---------------------------------------------------------------------------
_ALIAS_RE = re.compile(r"""\bAS\s+"?([a-zA-Z0-9_]+)"?\s*""", re.IGNORECASE)


def _extract_alias_columns(sql: str | None) -> list[str]:
    """Extract column names or aliases from SELECT projection SQL."""
    if not sql:
        return []
    upper = sql.upper()
    from_idx = upper.find("FROM ")
    select_clause = sql[:from_idx] if from_idx > 0 else sql
    matches = [m.group(1) for m in _ALIAS_RE.finditer(select_clause)]
    if matches:
        return matches
    # Fallback: comma-separated identifiers in SELECT clause
    cols = []
    cleaned = re.sub(r'(?i)^\s*SELECT\s+', '', select_clause)
    for part in cleaned.split(","):
        p = part.strip().split()
        if p:
            col_name = p[-1].strip('"\'` ')
            if col_name and col_name.upper() not in ("SELECT", "DISTINCT"):
                cols.append(col_name)
    return cols


def _extract_source_relation(sql: str | None) -> tuple[str | None, str | None]:
    """Extract (schema, table) from FROM clause in SQL string."""
    if not sql:
        return None, None
    m = re.search(r'FROM\s+["`]?([a-zA-Z0-9_]+)["`]?\s*\.\s*["`]?([a-zA-Z0-9_]+)["`]?', sql, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m2 = re.search(r'FROM\s+["`]?([a-zA-Z0-9_]+)["`]?', sql, re.IGNORECASE)
    if m2:
        return None, m2.group(1)
    return None, None


def _has_scn_binding(sql: str | None) -> bool:
    if not sql:
        return False
    return bool(re.search(r'AS\s+OF\s+SCN\s+\$\{?\w+\}?', sql, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Parser core
# ---------------------------------------------------------------------------
def parse_yaml(yaml_path: Path) -> tuple[dict[str, Any], list[JobEntity], list[Problem]]:
    problems: list[Problem] = []
    fname = yaml_path.name

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
            message="YAML root must be a mapping.",
            file_a=fname,
            stage="yaml_validation",
        ))
        return {}, [], problems

    # Global schema defaults
    global_src_schema = data.get("source", {}).get("schema") if isinstance(data.get("source"), dict) else None
    global_tgt_schema = data.get("target", {}).get("schema") if isinstance(data.get("target"), dict) else None

    # Global acquisition mode
    acquisition = data.get("acquisition")
    global_snapshot_req = (acquisition == "snapshot")

    # Locate jobs section: try 'job' or 'jobs'
    jobs_raw = data.get("job") if "job" in data else data.get("jobs")
    if jobs_raw is None:
        problems.append(Problem(
            type="MISSING_SECTION",
            severity=Severity.ERROR,
            message="Required top-level section 'job' or 'jobs' is missing.",
            file_a=fname,
            path_a="job",
            stage="yaml_validation",
        ))
        return data, [], problems

    # Normalize jobs_raw into list of (job_id, job_dict)
    normalized_jobs: list[tuple[str, dict]] = []
    if isinstance(jobs_raw, dict):
        for k, v in jobs_raw.items():
            if isinstance(v, dict):
                normalized_jobs.append((str(k), v))
    elif isinstance(jobs_raw, list):
        for idx, item in enumerate(jobs_raw):
            if isinstance(item, dict):
                jid = str(item.get("id") or item.get("job_id") or f"JOB_{idx+1}")
                normalized_jobs.append((jid, item))
    else:
        problems.append(Problem(
            type="YAML_STRUCTURE_ERROR",
            severity=Severity.ERROR,
            message="'job' section must be a mapping or list.",
            file_a=fname,
            path_a="job",
            stage="yaml_validation",
        ))
        return data, [], problems

    jobs: list[JobEntity] = []
    seen_job_ids: set[str] = set()

    for job_id, jdata in normalized_jobs:
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

        # ---- Parse Source ----
        src_info = jdata.get("source", {})
        src_info = src_info if isinstance(src_info, dict) else {}

        projection_sql = src_info.get("projection")
        src_table = src_info.get("table")
        src_schema = src_info.get("schema") or global_src_schema
        src_columns = src_info.get("columns", [])

        if projection_sql:
            parsed_schema, parsed_table = _extract_source_relation(projection_sql)
            if parsed_schema:
                src_schema = parsed_schema
            if parsed_table:
                src_table = parsed_table
            if not src_columns:
                src_columns = _extract_alias_columns(projection_sql)

        src_has_scn = _has_scn_binding(projection_sql)

        source_entity = SourceEntity(
            schema_name=src_schema,
            table_name=src_table,
            relation=src_info.get("projection_view") or src_table,
            columns=list(src_columns) if isinstance(src_columns, list) else [],
            projection_sql=projection_sql,
            snapshot_binding="${run_scn}" if src_has_scn else None,
        )

        # Raw relations fallback
        raw_rels = src_info.get("raw_relations", [])
        if isinstance(raw_rels, list):
            for rr in raw_rels:
                if isinstance(rr, dict):
                    if not source_entity.schema_name and rr.get("schema"):
                        source_entity.schema_name = rr["schema"]
                    if not source_entity.table_name and rr.get("table"):
                        source_entity.table_name = rr["table"]

        # ---- Parse Target ----
        tgt_info = jdata.get("target", {})
        tgt_info = tgt_info if isinstance(tgt_info, dict) else {}

        tgt_table = tgt_info.get("table")
        tgt_schema = tgt_info.get("schema") or global_tgt_schema
        tgt_columns = tgt_info.get("columns", [])
        tgt_relation = tgt_info.get("relation") or tgt_info.get("view")

        if isinstance(tgt_relation, str) and not tgt_table:
            m = re.match(r'["`]?([a-zA-Z0-9_]+)["`]?\s*\.\s*["`]?([a-zA-Z0-9_]+)["`]?', tgt_relation)
            if m:
                tgt_schema = m.group(1)
                tgt_table = m.group(2)
            else:
                tgt_table = tgt_relation.strip('"\'` ')

        if not tgt_columns:
            tgt_columns = source_entity.columns

        target_entity = TargetEntity(
            schema_name=tgt_schema,
            table_name=tgt_table,
            relation=tgt_relation if isinstance(tgt_relation, str) else tgt_table,
            columns=list(tgt_columns) if isinstance(tgt_columns, list) else [],
        )

        # ---- Snapshot / SCN requirements ----
        scn_snapshot = jdata.get("scn_snapshot", {})
        scn_req = False
        start_scn = None
        if isinstance(scn_snapshot, dict):
            scn_req = scn_snapshot.get("required", False)
            start_scn = scn_snapshot.get("start_scn")

        snapshot_required = global_snapshot_req or scn_req

        # ---- Column duplicate check ----
        cols = source_entity.columns
        if cols:
            seen_c: set[str] = set()
            for c in cols:
                c_str = str(c).lower()
                if c_str in seen_c:
                    problems.append(Problem(
                        type="DUPLICATE_COLUMN",
                        severity=Severity.ERROR,
                        message=f"Column '{c}' is declared more than once in job '{job_id}'.",
                        file_a=fname,
                        path_a=f"job.{job_id}.columns",
                        stage="yaml_validation",
                        job=job_id,
                    ))
                seen_c.add(c_str)

        # ---- Checks ----
        checks_data = jdata.get("check") or jdata.get("checks") or []
        checks_list = checks_data if isinstance(checks_data, list) else []

        job_entity = JobEntity(
            job_id=job_id,
            source=source_entity,
            target=target_entity,
            columns=cols,
            checks=[c for c in checks_list if isinstance(c, dict)],
            snapshot_required=snapshot_required,
            snapshot_binding=str(start_scn) if start_scn else None,
            raw_data=jdata,
        )
        jobs.append(job_entity)

    return data, jobs, problems
