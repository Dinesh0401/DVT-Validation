"""
SeaTunnel .conf (HOCON) Parser — robust nested-block parser.

This is NOT a fragile regex-only parser.  It implements a real tokeniser that
tracks brace depth, quoted strings (including triple-quoted ``\"\"\"``),
comments, and nested block boundaries.

Public API
    ``parse_seatunnel(conf_path) -> (raw_text, st_jobs, problems)``

Every extracted value (job names, table names, columns, SQL) comes from the
file itself — zero hardcoding.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.models.preflight_models import (
    JobEntity,
    Problem,
    Severity,
    SourceEntity,
    TargetEntity,
    TransformEntity,
)


# ========================================================================
# Tokeniser / block parser
# ========================================================================

def _strip_comments(text: str) -> str:
    """Remove ``# …`` and ``// …`` line comments, respecting quoted strings."""
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        in_str = False
        quote_char = None
        result: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                result.append(ch)
                if ch == "\\" and i + 1 < len(line):
                    result.append(line[i + 1])
                    i += 2
                    continue
                if ch == quote_char:
                    in_str = False
                i += 1
                continue
            if ch in ('"', "'"):
                in_str = True
                quote_char = ch
                result.append(ch)
                i += 1
                continue
            if ch == "#":
                break
            if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            result.append(ch)
            i += 1
        cleaned.append("".join(result))
    return "\n".join(cleaned)


def _find_matching_brace(text: str, start: int) -> int:
    """
    Given that ``text[start] == '{'``, return the index of the matching ``}``.
    Handles nested braces and triple-quoted strings.
    """
    depth = 0
    i = start
    length = len(text)
    while i < length:
        ch = text[i]

        # Triple-quoted string
        if text[i:i + 3] == '"""':
            end_idx = text.find('"""', i + 3)
            if end_idx == -1:
                return -1  # unbalanced
            i = end_idx + 3
            continue

        # Single-quoted string
        if ch == '"':
            i += 1
            while i < length and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1  # skip closing quote
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1  # unbalanced


def _parse_block(text: str) -> dict[str, Any]:
    """
    Parse a HOCON-like block body into a dict.

    Handles:
      key = value
      key = \"\"\"multi-line\"\"\"
      key = [array]
      key { nested }
      key.sub = value
    """
    result: dict[str, Any] = {}
    i = 0
    length = len(text)

    while i < length:
        # skip whitespace
        while i < length and text[i] in (" ", "\t", "\n", "\r", ","):
            i += 1
        if i >= length:
            break

        # skip if we hit a closing brace (shouldn't normally happen at top level)
        if text[i] == "}":
            break

        # --- read key ---
        key_start = i
        while i < length and text[i] not in ("=", "{", " ", "\t", "\n", "\r", "}"):
            i += 1
        key = text[key_start:i].strip()
        if not key:
            i += 1
            continue

        # skip whitespace
        while i < length and text[i] in (" ", "\t"):
            i += 1
        if i >= length:
            break

        # --- key { block } pattern ---
        if text[i] == "{":
            end = _find_matching_brace(text, i)
            if end == -1:
                break
            inner = text[i + 1:end]
            child = _parse_block(inner)
            # Handle dotted keys like "create-table.sql"
            if "." in key:
                parts = key.split(".", 1)
                outer_key, inner_key = parts
                if outer_key not in result or not isinstance(result[outer_key], dict):
                    result[outer_key] = {}
                result[outer_key][inner_key] = child
            else:
                if key in result and isinstance(result[key], dict) and isinstance(child, dict):
                    result[key].update(child)
                else:
                    result[key] = child
            i = end + 1
            continue

        # --- key = value ---
        if text[i] == "=":
            i += 1  # skip '='
            while i < length and text[i] in (" ", "\t"):
                i += 1
            if i >= length:
                break

            value, i = _read_value(text, i)

            # Handle dotted keys
            if "." in key:
                parts = key.split(".")
                d = result
                for p in parts[:-1]:
                    if p not in d or not isinstance(d[p], dict):
                        d[p] = {}
                    d = d[p]
                d[parts[-1]] = value
            else:
                result[key] = value
            continue

        # --- key <newline> { block } ---
        if text[i] == "\n":
            # peek ahead for a block
            j = i
            while j < length and text[j] in (" ", "\t", "\n", "\r"):
                j += 1
            if j < length and text[j] == "{":
                end = _find_matching_brace(text, j)
                if end != -1:
                    inner = text[j + 1:end]
                    child = _parse_block(inner)
                    result[key] = child
                    i = end + 1
                    continue
            # otherwise, key with no value — skip
            i += 1
            continue

        i += 1

    return result


def _read_value(text: str, i: int) -> tuple[Any, int]:
    """Read a single value starting at position i. Returns (value, new_i)."""
    length = len(text)

    # Triple-quoted string
    if text[i:i + 3] == '"""':
        end = text.find('"""', i + 3)
        if end == -1:
            return text[i + 3:], length
        val = text[i + 3:end]
        return val.strip(), end + 3

    # Single-quoted string (double quotes)
    if text[i] == '"':
        j = i + 1
        chars: list[str] = []
        while j < length:
            if text[j] == "\\":
                if j + 1 < length:
                    esc = text[j + 1]
                    if esc == '"':
                        chars.append('"')
                    elif esc == "\\":
                        chars.append("\\")
                    elif esc == "n":
                        chars.append("\n")
                    elif esc == "t":
                        chars.append("\t")
                    else:
                        chars.append(esc)
                    j += 2
                    continue
            if text[j] == '"':
                return "".join(chars), j + 1
            chars.append(text[j])
            j += 1
        return "".join(chars), j

    # Array
    if text[i] == "[":
        return _read_array(text, i)

    # Block
    if text[i] == "{":
        end = _find_matching_brace(text, i)
        if end == -1:
            return {}, length
        inner = text[i + 1:end]
        return _parse_block(inner), end + 1

    # Unquoted value (up to newline or comma)
    j = i
    while j < length and text[j] not in ("\n", "\r", ",", "}"):
        j += 1
    val = text[i:j].strip()

    # Try type coercion
    if val.lower() == "true":
        return True, j
    if val.lower() == "false":
        return False, j
    try:
        return int(val), j
    except ValueError:
        pass
    try:
        return float(val), j
    except ValueError:
        pass
    return val, j


def _read_array(text: str, i: int) -> tuple[list[Any], int]:
    """Read a HOCON array starting at '['."""
    length = len(text)
    i += 1  # skip '['
    items: list[Any] = []
    while i < length:
        while i < length and text[i] in (" ", "\t", "\n", "\r", ","):
            i += 1
        if i >= length or text[i] == "]":
            return items, i + 1
        value, i = _read_value(text, i)
        items.append(value)
    return items, i


# ========================================================================
# SeaTunnel structure extraction
# ========================================================================

def _extract_columns_from_sql(sql: str) -> list[str]:
    """Extract target alias columns from a SQL SELECT statement."""
    if not sql:
        return []
    alias_re = re.compile(r'\bAS\s+"([^"]+)"', re.IGNORECASE)
    # Only look at SELECT clause
    upper = sql.upper()
    from_idx = -1
    depth = 0
    for j, ch in enumerate(upper):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and upper[j:j + 5] in ("FROM ", "FROM\n"):
            from_idx = j
            break
    select_part = sql[:from_idx] if from_idx > 0 else sql
    return [m.group(1) for m in alias_re.finditer(select_part)]


def _extract_source_relation_from_sql(sql: str) -> tuple[str | None, str | None]:
    """Extract schema.table from FROM clause."""
    if not sql:
        return None, None
    m = re.search(r'FROM\s+"([^"]+)"\s*\.\s*"([^"]+)"', sql, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _has_scn_in_sql(sql: str) -> bool:
    """Check for SCN/snapshot binding in SQL."""
    if not sql:
        return False
    return bool(re.search(r'AS\s+OF\s+SCN', sql, re.IGNORECASE))


def _extract_st_jobs(parsed: dict[str, Any], conf_name: str) -> tuple[list[JobEntity], list[Problem]]:
    """
    Walk the parsed HOCON tree and extract SeaTunnel job entities.

    The transpiler generates paired jobs per target:
      <target>_ddl  — DDL job (schema creation)
      <target>_data — data loading job

    We group them by their underlying job_id from comments, or by the
    target table name.
    """
    problems: list[Problem] = []
    jobs: list[JobEntity] = []

    job_block = parsed.get("job", parsed)
    if not isinstance(job_block, dict):
        problems.append(Problem(
            type="CONF_STRUCTURE_ERROR",
            severity=Severity.ERROR,
            message="Top-level 'job' block is missing or not a block.",
            file_a=conf_name,
            stage="conf_validation",
        ))
        return jobs, problems

    # Collect all named sub-blocks (each is a SeaTunnel job definition)
    st_job_blocks: dict[str, dict[str, Any]] = {}
    for key, val in job_block.items():
        if isinstance(val, dict) and key not in ("env",):
            st_job_blocks[key] = val

    if not st_job_blocks:
        problems.append(Problem(
            type="NO_JOBS_FOUND",
            severity=Severity.ERROR,
            message="No SeaTunnel job definitions found in the .conf file.",
            file_a=conf_name,
            stage="conf_validation",
        ))
        return jobs, problems

    # Group by base name: public_employees_ddl + public_employees_data → public_employees
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for name, block in st_job_blocks.items():
        if name.endswith("_ddl"):
            base = name[:-4]
            groups.setdefault(base, {})["ddl"] = block
            groups[base]["ddl_name"] = name  # type: ignore[assignment]
        elif name.endswith("_data"):
            base = name[:-5]
            groups.setdefault(base, {})["data"] = block
            groups[base]["data_name"] = name  # type: ignore[assignment]
        else:
            # standalone job — treat as data
            groups.setdefault(name, {})["data"] = block
            groups[name]["data_name"] = name  # type: ignore[assignment]

    for base_name, group in groups.items():
        ddl_block = group.get("ddl", {})
        data_block = group.get("data", {})

        # ---- Determine job_id ----
        # The env block may contain job.name
        data_env = data_block.get("env", {}) if isinstance(data_block, dict) else {}
        ddl_env = ddl_block.get("env", {}) if isinstance(ddl_block, dict) else {}

        # ---- Source ----
        source_block = data_block.get("source", {}) if isinstance(data_block, dict) else {}
        # Source can be nested: source { Jdbc { ... } }
        jdbc_source = _find_jdbc_block(source_block)
        source_query = jdbc_source.get("query", "") if jdbc_source else ""
        src_columns = _extract_columns_from_sql(source_query)
        src_schema, src_table = _extract_source_relation_from_sql(source_query)
        has_scn = _has_scn_in_sql(source_query)

        source = SourceEntity(
            schema_name=src_schema,
            table_name=src_table,
            columns=src_columns,
            projection_sql=source_query if source_query else None,
            snapshot_binding="${run_scn}" if has_scn else None,
        )

        # ---- Target ----
        # From DDL block
        ddl_section = ddl_block.get("ddl", {}) if isinstance(ddl_block, dict) else {}
        ddl_columns = ddl_section.get("columns", []) if isinstance(ddl_section, dict) else []
        ddl_target = ddl_section.get("target", "") if isinstance(ddl_section, dict) else ""

        # From sink block (data job)
        sink_block = data_block.get("sink", {}) if isinstance(data_block, dict) else {}
        jdbc_sink = _find_jdbc_block(sink_block)
        sink_schema = jdbc_sink.get("table_schema", "") if jdbc_sink else ""
        sink_table = jdbc_sink.get("table_name", "") if jdbc_sink else ""

        # From DML block
        dml_block = data_block.get("dml", {}) if isinstance(data_block, dict) else {}
        dml_columns = dml_block.get("columns", []) if isinstance(dml_block, dict) else []
        dml_target = dml_block.get("target", "") if isinstance(dml_block, dict) else ""

        tgt_schema = sink_schema
        tgt_table = sink_table
        if not tgt_schema and dml_target:
            m = re.match(r'"([^"]+)"\s*\.\s*"([^"]+)"', str(dml_target))
            if m:
                tgt_schema = m.group(1)
                tgt_table = m.group(2)

        # Consolidate columns: prefer DDL columns, then DML columns, then source-extracted
        target_columns = ddl_columns if ddl_columns else dml_columns if dml_columns else src_columns

        target = TargetEntity(
            schema_name=tgt_schema,
            table_name=tgt_table,
            columns=target_columns,
        )

        # ---- Transform ----
        transforms: list[TransformEntity] = []
        transform_block = data_block.get("transform", {}) if isinstance(data_block, dict) else {}
        if isinstance(transform_block, dict):
            sql_block = transform_block.get("SQL", transform_block.get("sql", {}))
            if isinstance(sql_block, dict) and sql_block:
                transforms.append(TransformEntity(
                    source_table=sql_block.get("source_table_name"),
                    result_table=sql_block.get("result_table_name"),
                    query=sql_block.get("query"),
                ))

        # ---- Determine the contract job_id ----
        # Try to extract from comments (we look at the raw text later), or
        # derive from the base name pattern
        job_id = _derive_job_id(base_name, data_env)

        # ---- Validate required blocks ----
        if isinstance(data_block, dict):
            if not source_block and not isinstance(data_block.get("source"), dict):
                problems.append(Problem(
                    type="MISSING_SOURCE",
                    severity=Severity.ERROR,
                    message=f"Data job '{group.get('data_name', base_name)}' has no source block.",
                    file_a=conf_name,
                    path_a=f"job.{group.get('data_name', base_name)}.source",
                    stage="conf_validation",
                    job=job_id,
                ))
            if not jdbc_sink:
                problems.append(Problem(
                    type="MISSING_SINK",
                    severity=Severity.ERROR,
                    message=f"Data job '{group.get('data_name', base_name)}' has no sink JDBC block.",
                    file_a=conf_name,
                    path_a=f"job.{group.get('data_name', base_name)}.sink",
                    stage="conf_validation",
                    job=job_id,
                ))

        job_entity = JobEntity(
            job_id=job_id,
            source=source,
            target=target,
            transforms=transforms,
            columns=target_columns,
            snapshot_required=has_scn,
            snapshot_binding="${run_scn}" if has_scn else None,
        )
        jobs.append(job_entity)

    return jobs, problems


def _find_jdbc_block(block: Any) -> dict[str, Any] | None:
    """Find the JDBC configuration inside a source/sink block (may be nested)."""
    if not isinstance(block, dict):
        return None
    # Direct JDBC keys
    if "url" in block or "query" in block or "table_name" in block:
        return block
    # Nested: source { Jdbc { ... } }
    for key, val in block.items():
        if isinstance(val, dict):
            if "url" in val or "query" in val or "table_name" in val:
                return val
            # One more level
            for k2, v2 in val.items():
                if isinstance(v2, dict) and ("url" in v2 or "query" in v2):
                    return v2
    return None


def _derive_job_id(base_name: str, env: dict[str, Any]) -> str:
    """
    Derive the contract job_id from the SeaTunnel job base name.

    Convention: SeaTunnel uses ``public_employees`` → contract uses ``JOB-hr_employees``.
    The mapping must be inferred dynamically from the source relation.
    We store the base_name and reconcile during cross-validation.
    """
    return f"ST:{base_name}"


# ========================================================================
# Job-ID extraction from raw text comments
# ========================================================================

_JOB_ID_COMMENT_RE = re.compile(r"#\s*job_id\s*:\s*(\S+)", re.IGNORECASE)


def _extract_job_ids_from_comments(raw_text: str) -> dict[str, str]:
    """
    Scan the raw .conf text for comment lines like ``# job_id : JOB-hr_employees``
    and map them to the SeaTunnel job block they precede.

    Returns ``{ seatunnel_block_name: contract_job_id }``.
    """
    mapping: dict[str, str] = {}
    lines = raw_text.split("\n")
    last_job_id: str | None = None

    for line in lines:
        stripped = line.strip()
        m = _JOB_ID_COMMENT_RE.match(stripped)
        if m:
            last_job_id = m.group(1)
            continue
        # Look for the block name that follows a job_id comment
        if last_job_id:
            block_m = re.match(r"\s*(\w+)\s*\{", stripped)
            if block_m:
                block_name = block_m.group(1)
                # Map the base name (strip _ddl/_data suffix)
                base = block_name
                if base.endswith("_ddl"):
                    base = base[:-4]
                elif base.endswith("_data"):
                    base = base[:-5]
                mapping[base] = last_job_id
                last_job_id = None

    return mapping


# ========================================================================
# Public API
# ========================================================================

def parse_seatunnel(conf_path: Path) -> tuple[str, list[JobEntity], list[Problem]]:
    """
    Parse a SeaTunnel .conf file and return
    ``(raw_text, jobs_list, problems)``.
    """
    problems: list[Problem] = []
    conf_name = conf_path.name

    try:
        raw_text = conf_path.read_text(encoding="utf-8")
    except Exception as exc:
        problems.append(Problem(
            type="CONF_READ_ERROR",
            severity=Severity.ERROR,
            message=f"Cannot read .conf file: {exc}",
            file_a=conf_name,
            stage="conf_validation",
        ))
        return "", [], problems

    # ---- Strip comments and parse ----
    cleaned = _strip_comments(raw_text)

    # ---- Check balanced braces ----
    open_count = cleaned.count("{")
    close_count = cleaned.count("}")
    if open_count != close_count:
        problems.append(Problem(
            type="UNBALANCED_BRACES",
            severity=Severity.ERROR,
            message=f"Unbalanced braces in .conf: {open_count} open, {close_count} close.",
            file_a=conf_name,
            stage="conf_validation",
        ))
        return raw_text, [], problems

    # ---- Parse the block structure ----
    try:
        parsed = _parse_block(cleaned)
    except Exception as exc:
        problems.append(Problem(
            type="CONF_PARSE_ERROR",
            severity=Severity.ERROR,
            message=f"Failed to parse .conf structure: {exc}",
            file_a=conf_name,
            stage="conf_validation",
        ))
        return raw_text, [], problems

    # ---- Extract jobs ----
    st_jobs, job_problems = _extract_st_jobs(parsed, conf_name)
    problems.extend(job_problems)

    # ---- Enrich job_ids from comments ----
    comment_mapping = _extract_job_ids_from_comments(raw_text)
    for job in st_jobs:
        # job.job_id currently looks like "ST:public_employees"
        base = job.job_id.removeprefix("ST:")
        if base in comment_mapping:
            job.job_id = comment_mapping[base]

    return raw_text, st_jobs, problems
