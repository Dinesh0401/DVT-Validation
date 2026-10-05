#!/usr/bin/env python3
"""
extract_jobs.py — Generic Stage-1 Preflight Parser & Manifest Builder.

A fully dynamic, data-driven parser that extracts, aligns, and cross-verifies
the validation contract (duckdb.yaml) and migration execution plan (seatunnel.conf)
without hardcoding database types, table names, or job counts.

Outputs (generated/):
  jobs.json — complete structured manifest of all logical jobs.
"""

import argparse
import json
import re
import sys
from pathlib import Path
import yaml

# Ensure scripts dir is in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import (
    BASE, INPUT, GENERATED,
    infer_engine,
    parse_relation_identifier,
    normalize_relation,
    resolve_input_paths,
)


# ---------------------------------------------------------------------------
# 1. Parse contract (e.g. duckdb.yaml) dynamically
# ---------------------------------------------------------------------------
def extract_duckdb(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    jobs = {}
    for job_id, job in (doc.get("job", {}) or {}).items():
        checks = []
        for chk in job.get("check", []) or []:
            checks.append({
                "check_id": chk.get("check_id"),
                "type": chk.get("type"),
                "category": chk.get("category"),
                "severity": chk.get("severity"),
                "sql": chk.get("sql"),
                "runtime_strategy": chk.get("runtime_strategy"),
                "expected": chk.get("expected"),
            })

        target_info = job.get("target", {})
        source_info = job.get("source", {})

        jobs[job_id] = {
            "order": job.get("order"),
            "source_projection": (source_info.get("projection") or "").strip(),
            "target_relation": (target_info.get("relation") or "").strip(),
            "target_view": target_info.get("view"),
            "raw_relations": source_info.get("raw_relations", []),
            "checks": checks,
            "assumptions": job.get("assumptions", []),
            "env": job.get("env", {}),
        }

    # Discover blocked jobs dynamically from contract summary and header comments
    summary = doc.get("summary", {})
    blocked_jobs = list(summary.get("blocked_jobs", []))

    # Also scan comments in raw text for any un-emitted/blocked notice
    raw_text = path.read_text(encoding="utf-8")
    comment_blocked = re.findall(r'#\s*NOT\s+EMITTED\s*--.*?blocked.*?:\s*([A-Za-z0-9_\-]+)', raw_text, re.IGNORECASE)
    for b_id in comment_blocked:
        if b_id not in blocked_jobs:
            blocked_jobs.append(b_id)

    return {
        "version": doc.get("duckdb_jobs_version"),
        "produced_by": doc.get("produced_by"),
        "engine": doc.get("engine", {}),
        "acquisition": doc.get("acquisition"),
        "bindings": doc.get("bindings", {}),
        "convention": doc.get("convention", {}),
        "summary": summary,
        "blocked_jobs": blocked_jobs,
        "jobs": jobs,
    }


# ---------------------------------------------------------------------------
# 2. Parse execution plan (seatunnel.conf) with Generic Stateful Tokenizer
# ---------------------------------------------------------------------------
def extract_seatunnel(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    # Detect engines from top-level metadata comments if present
    src_eng_m = re.search(r'#\s*source engine\s*:\s*([A-Za-z0-9_]+)', text, re.IGNORECASE)
    tgt_eng_m = re.search(r'#\s*target engine\s*:\s*([A-Za-z0-9_]+)', text, re.IGNORECASE)
    acq_m = re.search(r'#\s*acquisition\s*:\s*([A-Za-z0-9_]+)', text, re.IGNORECASE)

    meta = {
        "source_engine": infer_engine(comment_str=src_eng_m.group(1)) if src_eng_m else None,
        "target_engine": infer_engine(comment_str=tgt_eng_m.group(1)) if tgt_eng_m else None,
        "acquisition": acq_m.group(1).lower() if acq_m else "snapshot",
    }

    # Parse all top-level blocks inside `job { ... }` or at root
    # Generic block pattern matching `<identifier> {`
    block_pattern = re.compile(r'(\b[a-zA-Z0-9_]+)\s*\{')
    matches = list(block_pattern.finditer(text))

    raw_blocks = {}
    for i, m in enumerate(matches):
        bname = m.group(1)
        if bname.lower() in ("job", "env", "source", "sink", "transform", "dml", "ddl", "jdbc", "sql", "properties"):
            continue  # skip inner component block names

        bstart = m.start()
        prev_end = matches[i - 1].end() if i > 0 else 0
        preceding = text[prev_end:bstart]
        comment_lines = []
        for line in reversed(preceding.splitlines()):
            ls = line.strip()
            if ls.startswith('#') or ls == '':
                comment_lines.append(line)
            else:
                break
        header = '\n'.join(reversed(comment_lines))

        # Balanced brace counter with quote awareness
        brace_open_idx = text.find('{', m.end() - 1)
        depth = 1
        idx = brace_open_idx + 1
        in_triple = False
        in_double = False
        in_single = False

        while idx < len(text) and depth > 0:
            if text[idx:idx + 3] == '"""':
                in_triple = not in_triple
                idx += 3
                continue
            if in_triple:
                idx += 1
                continue
            c = text[idx]
            if c == '#' and not in_double and not in_single:
                eol = text.find('\n', idx)
                idx = len(text) if eol == -1 else eol + 1
                continue
            if c == '"' and not in_single:
                if idx > 0 and text[idx - 1] == '\\':
                    pass
                else:
                    in_double = not in_double
                idx += 1
                continue
            if c == "'" and not in_double:
                if idx > 0 and text[idx - 1] == '\\':
                    pass
                else:
                    in_single = not in_single
                idx += 1
                continue
            if in_double or in_single:
                idx += 1
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            idx += 1

        content = text[bstart:idx]
        if not re.search(r'\benv\s*\{', content):
            continue

        # Extract annotations from header
        jid_m = re.search(r'#\s*job_id\s*:\s*(.+)', header)
        role_m = re.search(r'#\s*role\s*:\s*(.+)', header)
        kind_m = re.search(r'#\s*job kind\s*:\s*(.+)', header)
        src_m = re.search(r'#\s*source\s*:\s*(.+)', header)
        tgt_m = re.search(r'#\s*target\s*:\s*(.+)', header)
        pk_m = re.search(r'#\s*primary key\s*:\s*(.+)', header)

        # Detect JDBC drivers and URLs inside the block
        src_driver_m = re.search(r'source\s*\{[^}]*?driver\s*=\s*"([^"]+)"', content, re.DOTALL | re.IGNORECASE)
        tgt_driver_m = re.search(r'sink\s*\{[^}]*?driver\s*=\s*"([^"]+)"', content, re.DOTALL | re.IGNORECASE)
        src_url_m = re.search(r'source\s*\{[^}]*?url\s*=\s*"([^"]+)"', content, re.DOTALL | re.IGNORECASE)
        tgt_url_m = re.search(r'sink\s*\{[^}]*?url\s*=\s*"([^"]+)"', content, re.DOTALL | re.IGNORECASE)

        # Dynamically infer engine if not already detected from headers
        if not meta["source_engine"]:
            src_driver = src_driver_m.group(1) if src_driver_m else ""
            src_url = src_url_m.group(1) if src_url_m else ""
            eng = infer_engine(driver_str=src_driver, url_str=src_url)
            if eng != "GenericSQL":
                meta["source_engine"] = eng

        if not meta["target_engine"]:
            tgt_driver = tgt_driver_m.group(1) if tgt_driver_m else ""
            tgt_url = tgt_url_m.group(1) if tgt_url_m else ""
            eng = infer_engine(driver_str=tgt_driver, url_str=tgt_url)
            if eng != "GenericSQL":
                meta["target_engine"] = eng

        # Extract statements inside HOCON (supports """ or " quoting)
        create_table_m = re.search(r'(?:create-table\.sql|create_table|create_table_sql)\s*=\s*(?:"""(.*?)"""|"([^"]+)")', content, re.DOTALL)
        create_table_sql = (create_table_m.group(1) or create_table_m.group(2)).strip() if create_table_m else None

        source_query_m = re.search(r'source\s*\{[^}]*?Jdbc\s*\{.*?query\s*=\s*(?:"""(.*?)"""|"([^"]+)").*?\}', content, re.DOTALL)
        source_query_sql = (source_query_m.group(1) or source_query_m.group(2)).strip() if source_query_m else None

        dml_m = re.search(r'dml\s*\{.*?statement\s*=\s*(?:"""(.*?)"""|"([^"]+)").*?\}', content, re.DOTALL)
        dml_statement = (dml_m.group(1) or dml_m.group(2)).strip() if dml_m else None

        transform_m = re.search(r'transform\s*\{.*?query\s*=\s*(?:"""(.*?)"""|"([^"]+)").*?\}', content, re.DOTALL)
        transform_query = (transform_m.group(1) or transform_m.group(2)).strip() if transform_m else None

        # Extract target relation inside block
        target_in_block = re.search(r'target\s*=\s*["\']?\\?"?([^"\'\\]+)\\?"?["\']?', content)

        # Extract primary key from DDL if defined
        pk_from_ddl = None
        if create_table_sql:
            pk_match = re.search(r'PRIMARY\s+KEY\s*\(\s*["\']?([^"\'\)]+)["\']?\s*\)', create_table_sql, re.IGNORECASE)
            if pk_match:
                pk_from_ddl = pk_match.group(1).strip()

        raw_blocks[bname] = {
            "name": bname,
            "header": header,
            "job_id": jid_m.group(1).strip() if jid_m else None,
            "role": role_m.group(1).strip() if role_m else None,
            "kind": kind_m.group(1).strip() if kind_m else None,
            "source": src_m.group(1).strip() if src_m else None,
            "target": tgt_m.group(1).strip() if tgt_m else None,
            "primary_key": pk_from_ddl or (pk_m.group(1).strip() if pk_m else None),
            "target_in_block": target_in_block.group(1).strip() if target_in_block else None,
            "create_table_sql": create_table_sql,
            "source_query": source_query_sql,
            "dml_statement": dml_statement,
            "transform_query": transform_query,
            "content": content,
        }

    # Group into logical jobs by job_id or target relation
    logical_jobs = {}
    for bname, b in raw_blocks.items():
        jid = b["job_id"] or bname
        entry = logical_jobs.setdefault(jid, {
            "job_id": jid,
            "kind": b.get("kind"),
            "source": b.get("source"),
            "target": b.get("target"),
            "primary_key": b.get("primary_key"),
            "ddl_block": None,
            "data_block": None,
        })
        is_ddl = b.get("create_table_sql") is not None or bname.endswith("_ddl") or "create" in (b.get("role") or "").lower()
        if is_ddl:
            entry["ddl_block"] = b
            if b.get("primary_key"):
                entry["primary_key"] = b.get("primary_key")
        else:
            entry["data_block"] = b
            entry["source_query"] = b.get("source_query")
            entry["dml_statement"] = b.get("dml_statement")
            entry["transform_query"] = b.get("transform_query")

    return {
        "metadata": meta,
        "logical_jobs": logical_jobs,
    }


# ---------------------------------------------------------------------------
# 3. Dynamic Relation & Job Cross-Verification
# ---------------------------------------------------------------------------
def classify_and_cross_verify(duckdb_data: dict, seatunnel_data: dict) -> list:
    duckdb_jobs = duckdb_data["jobs"]
    seatunnel_jobs = seatunnel_data["logical_jobs"]
    blocked_job_ids = duckdb_data.get("blocked_jobs", [])

    results = []
    processed_seat_jobs = set()

    for jid, d_info in duckdb_jobs.items():
        s_info = seatunnel_jobs.get(jid)

        # If not matched by exact job_id, attempt fallback match by normalized target relation
        target_duck = normalize_relation(d_info.get("target_relation", ""))
        if not s_info:
            for sj_id, sj_val in seatunnel_jobs.items():
                if normalize_relation(sj_val.get("target", "")) == target_duck:
                    s_info = sj_val
                    break

        raw_rels = [normalize_relation(r.get("relation", "")) for r in d_info.get("raw_relations", [])]
        seat_src = normalize_relation(s_info.get("source", "")) if s_info else ""
        target_seat = normalize_relation(s_info.get("target", "")) if s_info else ""

        if s_info:
            processed_seat_jobs.add(s_info.get("job_id"))
            target_match = (target_duck == target_seat)
            source_match = (seat_src in raw_rels or not raw_rels)

            status = "READY"
            reasons = []
            if not target_match:
                status = "REVIEW"
                reasons.append(f"Target mismatch: Contract '{target_duck}' vs Plan '{target_seat}'")
            if not source_match:
                status = "REVIEW"
                reasons.append(f"Source mismatch: Plan source '{seat_src}' not in Contract raw relations {raw_rels}")

            results.append({
                "job_id": jid,
                "order": d_info.get("order"),
                "status": status,
                "reason": " | ".join(reasons) if reasons else "",
                "target_match": target_match,
                "source_match": source_match,
                "duckdb": d_info,
                "seatunnel": s_info,
            })
        else:
            results.append({
                "job_id": jid,
                "order": d_info.get("order"),
                "status": "BLOCKED",
                "reason": "Job present in contract but missing from execution plan",
                "target_match": False,
                "source_match": False,
                "duckdb": d_info,
                "seatunnel": None,
            })

    # Record blocked jobs declared in contract
    for b_jid in blocked_job_ids:
        if b_jid not in [r["job_id"] for r in results]:
            results.append({
                "job_id": b_jid,
                "order": None,
                "status": "BLOCKED",
                "reason": "Explicitly blocked in migration specification (no query emitted by transpiler)",
                "target_match": False,
                "source_match": False,
                "duckdb": None,
                "seatunnel": None,
            })

    # Record any orphan execution plan jobs
    for s_jid, s_info in seatunnel_jobs.items():
        if s_jid not in processed_seat_jobs and s_jid not in [r["job_id"] for r in results]:
            results.append({
                "job_id": s_jid,
                "order": None,
                "status": "REVIEW",
                "reason": f"Execution plan job '{s_jid}' has no entry in validation contract",
                "target_match": False,
                "source_match": False,
                "duckdb": None,
                "seatunnel": s_info,
            })

    results.sort(key=lambda x: (x.get("order") if x.get("order") is not None else 999, x.get("job_id") or ""))
    return results


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generic Stage-1 Preflight Manifest Extractor (No Hardcoding)")
    parser.add_argument("--contract", "-c", help="Path to migration contract YAML (e.g. duckdb.yaml)")
    parser.add_argument("--plan", "-p", help="Path to execution plan (e.g. seatunnel.conf)")
    args = parser.parse_args()

    contract_path, plan_path = resolve_input_paths(args.contract, args.plan)

    if not contract_path or not contract_path.exists():
        print(f"FATAL: Migration contract YAML not found. Checked: {contract_path}", file=sys.stderr)
        return 1

    if not plan_path or not plan_path.exists():
        print(f"FATAL: Migration execution plan not found. Checked: {plan_path}", file=sys.stderr)
        return 1

    print(f"Loading Contract : {contract_path}")
    print(f"Loading Plan     : {plan_path}")

    duckdb_data = extract_duckdb(contract_path)
    seatunnel_data = extract_seatunnel(plan_path)
    classified = classify_and_cross_verify(duckdb_data, seatunnel_data)

    manifest = {
        "metadata": {
            "source_duckdb": str(contract_path),
            "source_seatunnel": str(plan_path),
            "detected_source_engine": seatunnel_data["metadata"].get("source_engine") or "Unknown",
            "detected_target_engine": seatunnel_data["metadata"].get("target_engine") or "Unknown",
            "acquisition": duckdb_data.get("acquisition") or seatunnel_data["metadata"].get("acquisition"),
            "bindings": duckdb_data.get("bindings", {}),
            "convention": duckdb_data.get("convention", {}),
            "duckdb_summary": duckdb_data.get("summary", {}),
        },
        "total_logical_jobs": len(classified),
        "jobs": classified,
    }

    GENERATED.mkdir(parents=True, exist_ok=True)
    out_path = GENERATED / "jobs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    counts = {"READY": 0, "BLOCKED": 0, "REVIEW": 0}
    for j in classified:
        counts[j["status"]] += 1

    print(f"Dynamically Parsed {len(classified)} Logical Jobs:")
    print(f"  Source Engine   : {manifest['metadata']['detected_source_engine']}")
    print(f"  Target Engine   : {manifest['metadata']['detected_target_engine']}")
    print(f"  Active Verified : {counts['READY']}")
    print(f"  Blocked Jobs    : {counts['BLOCKED']} -- {[j['job_id'] for j in classified if j['status'] == 'BLOCKED']}")
    print(f"  Review Jobs     : {counts['REVIEW']} -- {[j['job_id'] for j in classified if j['status'] == 'REVIEW']}")
    print(f"Wrote validated manifest to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
