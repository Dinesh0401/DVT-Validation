"""
SeaTunnel .conf (HOCON) Parser — robust nested-block parser.

Handles both SeaTunnel layout conventions:
  Layout 1 (Multi-job wrapper):
    job {
       public_employees_data {
          source { ... }
          transform { ... }
          sink { ... }
       }
    }

  Layout 2 (Single execution pipeline):
    env { ... }
    source { ... }
    transform { ... }
    sink { ... }
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
    depth = 0
    i = start
    length = len(text)
    while i < length:
        ch = text[i]

        if text[i:i + 3] == '"""':
            end_idx = text.find('"""', i + 3)
            if end_idx == -1:
                return -1
            i = end_idx + 3
            continue

        if ch == '"':
            i += 1
            while i < length and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _parse_block(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    i = 0
    length = len(text)

    while i < length:
        while i < length and text[i] in (" ", "\t", "\n", "\r", ","):
            i += 1
        if i >= length or text[i] == "}":
            break

        key_start = i
        while i < length and text[i] not in ("=", "{", " ", "\t", "\n", "\r", "}"):
            i += 1
        key = text[key_start:i].strip()
        if not key:
            i += 1
            continue

        while i < length and text[i] in (" ", "\t"):
            i += 1
        if i >= length:
            break

        if text[i] == "{":
            end = _find_matching_brace(text, i)
            if end == -1:
                break
            inner = text[i + 1:end]
            child = _parse_block(inner)
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

        if text[i] == "=":
            i += 1
            while i < length and text[i] in (" ", "\t"):
                i += 1
            if i >= length:
                break

            value, i = _read_value(text, i)

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

        if text[i] == "\n":
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
            i += 1
            continue

        i += 1

    return result


def _read_value(text: str, i: int) -> tuple[Any, int]:
    length = len(text)

    if text[i:i + 3] == '"""':
        end = text.find('"""', i + 3)
        if end == -1:
            return text[i + 3:], length
        val = text[i + 3:end]
        return val.strip(), end + 3

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

    if text[i] == "[":
        return _read_array(text, i)

    if text[i] == "{":
        end = _find_matching_brace(text, i)
        if end == -1:
            return {}, length
        inner = text[i + 1:end]
        return _parse_block(inner), end + 1

    j = i
    while j < length and text[j] not in ("\n", "\r", ",", "}"):
        j += 1
    val = text[i:j].strip()

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
    length = len(text)
    i += 1
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
# Helper extraction functions
# ========================================================================

def _extract_columns_from_sql(sql: str) -> list[str]:
    if not sql:
        return []
    alias_re = re.compile(r'\bAS\s+"?([a-zA-Z0-9_]+)"?', re.IGNORECASE)
    upper = sql.upper()
    from_idx = upper.find("FROM ")
    select_part = sql[:from_idx] if from_idx > 0 else sql
    matches = [m.group(1) for m in alias_re.finditer(select_part)]
    if matches:
        return matches
    # Fallback to field extraction
    cleaned = re.sub(r'(?i)^\s*SELECT\s+', '', select_part)
    cols = []
    for part in cleaned.split(","):
        p = part.strip().split()
        if p:
            col_name = p[-1].strip('"\'` ')
            if col_name and col_name.upper() not in ("SELECT", "DISTINCT", "*"):
                cols.append(col_name)
    return cols


def _extract_source_relation_from_sql(sql: str) -> tuple[str | None, str | None]:
    if not sql:
        return None, None
    m = re.search(r'FROM\s+["`]?([a-zA-Z0-9_]+)["`]?\s*\.\s*["`]?([a-zA-Z0-9_]+)["`]?', sql, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m2 = re.search(r'FROM\s+["`]?([a-zA-Z0-9_]+)["`]?', sql, re.IGNORECASE)
    if m2:
        return None, m2.group(1)
    return None, None


def _has_scn_in_sql(sql: str) -> bool:
    if not sql:
        return False
    return bool(re.search(r'AS\s+OF\s+SCN', sql, re.IGNORECASE))


def _find_plugin_block(block: Any) -> dict[str, Any] | None:
    """Extract table/query properties from source or sink plugin blocks."""
    if not isinstance(block, dict):
        return None
    if any(k in block for k in ("table", "table-name", "table_name", "query", "url", "schema-name", "schema_name")):
        return block
    for val in block.values():
        if isinstance(val, dict):
            if any(k in val for k in ("table", "table-name", "table_name", "query", "url", "schema-name", "schema_name")):
                return val
            for v2 in val.values():
                if isinstance(v2, dict) and any(k in v2 for k in ("table", "table-name", "table_name", "query", "url")):
                    return v2
    return None


def _extract_single_job(data_block: dict[str, Any], job_id: str, conf_name: str) -> tuple[JobEntity, list[Problem]]:
    """Extract a JobEntity from a single job block containing source/transform/sink."""
    problems: list[Problem] = []

    # Source block
    src_block = data_block.get("source", {})
    plugin_src = _find_plugin_block(src_block) or (src_block if isinstance(src_block, dict) else {})

    src_query = plugin_src.get("query", "")
    src_table = plugin_src.get("table-name") or plugin_src.get("table_name") or plugin_src.get("table")
    src_schema = plugin_src.get("schema-name") or plugin_src.get("schema_name") or plugin_src.get("schema")

    if src_query:
        p_schema, p_table = _extract_source_relation_from_sql(src_query)
        if p_schema:
            src_schema = p_schema
        if p_table:
            src_table = p_table

    src_columns = _extract_columns_from_sql(src_query)
    has_scn = _has_scn_in_sql(src_query)

    source = SourceEntity(
        schema_name=src_schema,
        table_name=src_table,
        relation=src_table,
        columns=src_columns,
        projection_sql=src_query if src_query else None,
        snapshot_binding="${run_scn}" if has_scn else None,
    )

    # Transform block
    transforms: list[TransformEntity] = []
    t_block = data_block.get("transform", {})
    if isinstance(t_block, dict):
        sql_t = _find_plugin_block(t_block) or t_block
        if isinstance(sql_t, dict) and sql_t:
            query = sql_t.get("query")
            if query and not src_columns:
                src_columns = _extract_columns_from_sql(query)
                source.columns = src_columns
            transforms.append(TransformEntity(
                source_table=sql_t.get("source_table_name"),
                result_table=sql_t.get("result_table_name"),
                query=query,
            ))

    # Sink block
    sink_block = data_block.get("sink", {})
    plugin_sink = _find_plugin_block(sink_block) or (sink_block if isinstance(sink_block, dict) else {})

    tgt_table = plugin_sink.get("table") or plugin_sink.get("table_name") or plugin_sink.get("table-name")
    tgt_schema = plugin_sink.get("table_schema") or plugin_sink.get("schema-name") or plugin_sink.get("schema")

    if isinstance(tgt_table, str) and "." in tgt_table and not tgt_schema:
        parts = tgt_table.split(".", 1)
        tgt_schema, tgt_table = parts[0], parts[1]

    target = TargetEntity(
        schema_name=tgt_schema,
        table_name=tgt_table,
        relation=tgt_table,
        columns=src_columns,
    )

    # Validations
    if not plugin_src:
        problems.append(Problem(
            type="MISSING_SOURCE",
            severity=Severity.ERROR,
            message=f"Job '{job_id}' has no valid source definition.",
            file_a=conf_name,
            path_a=f"job.{job_id}.source",
            stage="conf_validation",
            job=job_id,
        ))
    if not plugin_sink:
        problems.append(Problem(
            type="MISSING_SINK",
            severity=Severity.ERROR,
            message=f"Job '{job_id}' has no valid sink definition.",
            file_a=conf_name,
            path_a=f"job.{job_id}.sink",
            stage="conf_validation",
            job=job_id,
        ))

    job_entity = JobEntity(
        job_id=job_id,
        source=source,
        target=target,
        transforms=transforms,
        columns=src_columns,
        snapshot_required=has_scn,
        snapshot_binding="${run_scn}" if has_scn else None,
        raw_data=data_block,
    )

    return job_entity, problems


# ========================================================================
# Main extraction logic
# ========================================================================

def _extract_st_jobs(parsed: dict[str, Any], conf_name: str) -> tuple[list[JobEntity], list[Problem]]:
    problems: list[Problem] = []
    jobs: list[JobEntity] = []

    # Check if this is Layout 2 (top-level source and sink)
    if "source" in parsed and "sink" in parsed:
        job, job_probs = _extract_single_job(parsed, "ST:default", conf_name)
        return [job], job_probs

    # Layout 1 (wrapped in job { ... } or top-level named blocks)
    job_block = parsed.get("job", parsed)
    if not isinstance(job_block, dict):
        problems.append(Problem(
            type="CONF_STRUCTURE_ERROR",
            severity=Severity.ERROR,
            message="Top-level configuration structure invalid.",
            file_a=conf_name,
            stage="conf_validation",
        ))
        return jobs, problems

    # Collect sub-blocks containing source or sink
    st_job_blocks: dict[str, dict[str, Any]] = {}
    for key, val in job_block.items():
        if isinstance(val, dict) and key not in ("env",):
            # Check if this sub-block is itself a job (contains source/sink/ddl/dml)
            if any(k in val for k in ("source", "sink", "ddl", "dml", "transform")):
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

    # Group by base name (_ddl, _data)
    groups: dict[str, dict[str, Any]] = {}
    for name, block in st_job_blocks.items():
        if name.endswith("_ddl"):
            base = name[:-4]
            groups.setdefault(base, {})["ddl"] = block
            groups[base]["ddl_name"] = name
        elif name.endswith("_data"):
            base = name[:-5]
            groups.setdefault(base, {})["data"] = block
            groups[base]["data_name"] = name
        else:
            groups.setdefault(name, {})["data"] = block
            groups[name]["data_name"] = name

    for base_name, group in groups.items():
        data_block = group.get("data", group.get("ddl", {}))
        job_id = f"ST:{base_name}"
        job, job_probs = _extract_single_job(data_block, job_id, conf_name)

        # Merge DDL info if present
        ddl_block = group.get("ddl", {})
        if ddl_block:
            ddl_sec = ddl_block.get("ddl", {})
            if isinstance(ddl_sec, dict):
                ddl_tgt = ddl_sec.get("target")
                if ddl_tgt and not job.target.table_name:
                    job.target.relation = str(ddl_tgt)

        problems.extend(job_probs)
        jobs.append(job)

    return jobs, problems


def _extract_job_ids_from_comments(raw_text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    lines = raw_text.split("\n")
    last_job_id: str | None = None
    re_comment = re.compile(r"#\s*job_id\s*:\s*(\S+)", re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        m = re_comment.match(stripped)
        if m:
            last_job_id = m.group(1)
            continue
        if last_job_id:
            block_m = re.match(r"\s*(\w+)\s*\{", stripped)
            if block_m:
                block_name = block_m.group(1)
                base = block_name.removesuffix("_ddl").removesuffix("_data")
                mapping[base] = last_job_id
                last_job_id = None

    return mapping


def parse_seatunnel(conf_path: Path) -> tuple[str, list[JobEntity], list[Problem]]:
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

    cleaned = _strip_comments(raw_text)

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

    st_jobs, job_problems = _extract_st_jobs(parsed, conf_name)
    problems.extend(job_problems)

    comment_mapping = _extract_job_ids_from_comments(raw_text)
    for job in st_jobs:
        base = job.job_id.removeprefix("ST:")
        if base in comment_mapping:
            job.job_id = comment_mapping[base]

    return raw_text, st_jobs, problems
