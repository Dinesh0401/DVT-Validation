#!/usr/bin/env python3
"""
extract_jobs.py — Stage 1 preflight: parse the two input files and emit a
structured JSON manifest that every later step consumes.

Inputs  (input/):
  duckdb.yaml      validation contract (11 jobs + 1 blocked)
  seatunnel.conf   migration execution plan (22 SeaTunnel jobs)

Output (generated/):
  jobs.json        one record per logical job with source/target/checks/DDL/DML

No database is touched.  Nothing is executed.
"""

import json, re, sys
from pathlib import Path

import yaml  # PyYAML

BASE = Path(__file__).resolve().parent.parent
INPUT = BASE / "input"
GENERATED = BASE / "generated"


# ---------------------------------------------------------------------------
# 1. Parse duckdb.yaml
# ---------------------------------------------------------------------------
def extract_duckdb(path: Path) -> dict:
    with open(path) as f:
        doc = yaml.safe_load(f)

    jobs = {}
    for job_id, job in doc.get("job", {}).items():
        checks = []
        for chk in job.get("check", []) or []:
            checks.append({
                "check_id":   chk["check_id"],
                "type":       chk["type"],
                "category":   chk.get("category"),
                "severity":   chk.get("severity"),
                "sql":        chk.get("sql"),
                "runtime_strategy": chk.get("runtime_strategy"),
                "expected":   chk.get("expected"),
            })
        jobs[job_id] = {
            "order":          job.get("order"),
            "source_projection": job["source"]["projection"].strip(),
            "target_relation":   job["target"]["relation"].strip(),
            "raw_relations":     job["source"].get("raw_relations", []),
            "checks":           checks,
            "assumptions":      job.get("assumptions", []),
            "env":              job.get("env", {}),
        }
    summary = doc.get("summary", {})
    return {"jobs": jobs, "summary": summary, "convention": doc.get("convention", {})}


# ---------------------------------------------------------------------------
# 2. Parse seatunnel.conf
# ---------------------------------------------------------------------------
def extract_seatunnel(path: Path) -> dict:
    text = path.read_text()

    # Pull out each inner block:  shop_xxx_ddl { ... }  and  shop_xxx_data { ... }
    # Top-level wrapper is:  job { ... }  — we skip it and parse the inner blocks directly.
    blocks = re.findall(r'(shop_\S+?)_ddl\s*\{', text)
    logical = {}

    for name in blocks:
        job_id = f"JOB-{name}"

        # Extract the _ddl block
        ddl_pat = rf'{re.escape(name)}_ddl\s*\((.*?)\)\s*\{{'
        ddl_match = re.search(rf'{re.escape(name)}_ddl\s*\{{(.*?)\n  \}}', text, re.DOTALL)

        # Extract the _data block
        data_match = re.search(rf'{re.escape(name)}_data\s*\{{(.*?)\n  \}}', text, re.DOTALL)

        entry = logical.setdefault(job_id, {"kind": "transform", "role": "",
                                            "target": "", "ddl": None, "data": None})

        if ddl_match:
            entry["ddl"] = ddl_match.group(0)
            # role from comment block preceding ddl
            idx = text.find(ddl_match.group(0))
            pre = text[max(0, idx - 600):idx]
            m_role = re.search(r'# role\s*:\s*(.+)', pre)
            if m_role:
                entry["role"] = m_role.group(1).strip().lower()
            # target can use either double or single quotes inside the ddl
            m_tgt = re.search(r'target\s*=\s*(.+)$', ddl_match.group(0), re.MULTILINE)
            if m_tgt:
                entry["target"] = m_tgt.group(1).strip()

        if data_match:
            entry["data"] = data_match.group(0)

    # Extract source query + dml from data blocks
    for job_id, entry in logical.items():
        data = entry.get("data") or ""
        src_q = re.search(r'query\s*=\s*"""(.*?)"""', data, re.DOTALL)
        dml_s = re.search(r'statement\s*=\s*"""(.*?)"""', data, re.DOTALL)
        entry["source_query"] = src_q.group(1).strip() if src_q else None
        entry["dml_statement"] = dml_s.group(1).strip() if dml_s else None
        tr_q = re.search(r'query\s*=\s*"([^"]*)"', data)
        entry["transform_sql"] = tr_q.group(1) if tr_q else None

    return logical


# ---------------------------------------------------------------------------
# 3. Classify each logical job — match on target relation, not job name
# ---------------------------------------------------------------------------
def classify(duckdb_jobs: dict, seatunnel_jobs: dict) -> list:
    """Match SeaTunnel → duckdb by normalized target relation."""
    # Normalise target relation: strip quotes, lower, collapse
    def norm_rel(rel: str) -> str:
        # Strip backslash-escaped quotes (HOCON), outer quotes, whitespace
        s = rel.replace('\\', '')
        s = s.strip('"').strip("'")
        return s.lower()

    # Build SeaTunnel target index
    tgt_to_seatunnel = {}
    for job_id, entry in seatunnel_jobs.items():
        tgt = norm_rel(entry.get("target", ""))
        if tgt:
            tgt_to_seatunnel[tgt] = job_id

    # Build duckdb target index
    tgt_to_duckdb = {}
    for job_id, entry in duckdb_jobs.items():
        tgt = norm_rel(entry.get("target_relation", ""))
        if tgt:
            tgt_to_duckdb[tgt] = job_id

    # Map known cross-name aliases:
    #   shop_client (seatunnel) ↔ shop_customer (duckdb, because target is "shop"."client"??)
    # Actually duckdb target_relation for the customer job is "shop"."client"
    # while seatunnel job name is shop_client. Let's check.
    # For safety, log unmatched.

    out = []
    matched_seatunnel = set()
    matched_duckdb = set()

    # Match by normalized target relation
    for tgt, d_id in tgt_to_duckdb.items():
        s_id = tgt_to_seatunnel.get(tgt)
        if s_id:
            matched_seatunnel.add(s_id)
            matched_duckdb.add(d_id)
            out.append({
                "job_id": d_id,
                "seatunnel_job_id": s_id,
                "status": "READY",
                "reason": "",
                "duckdb": duckdb_jobs[d_id],
                "seatunnel": seatunnel_jobs[s_id],
            })
        else:
            matched_duckdb.add(d_id)
            out.append({
                "job_id": d_id,
                "seatunnel_job_id": None,
                "status": "BLOCKED",
                "reason": f"Target relation {tgt} has no SeaTunnel job",
                "duckdb": duckdb_jobs[d_id],
                "seatunnel": None,
            })

    # SeaTunnel jobs with no duckdb match
    for s_id, entry in seatunnel_jobs.items():
        if s_id in matched_seatunnel:
            continue
        tgt = norm_rel(entry.get("target", ""))
        if tgt in tgt_to_duckdb:
            continue  # already handled
        out.append({
            "job_id": None,
            "seatunnel_job_id": s_id,
            "status": "REVIEW",
            "reason": f"SeaTunnel job {s_id} (target {tgt}) has no duckdb.yaml entry",
            "duckdb": None,
            "seatunnel": entry,
        })

    return out


# ---------------------------------------------------------------------------
def main():
    duckdb = extract_duckdb(INPUT / "duckdb.yaml")
    seat  = extract_seatunnel(INPUT / "seatunnel.conf")
    classified = classify(duckdb["jobs"], seat)

    manifest = {
        "source_duckdb":  str(INPUT / "duckdb.yaml"),
        "source_seatunnel": str(INPUT / "seatunnel.conf"),
        "duckdb_summary":  duckdb["summary"],
        "convention":      duckdb["convention"],
        "jobs":            classified,
    }

    GENERATED.mkdir(parents=True, exist_ok=True)
    out_path = GENERATED / "jobs.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    # Compact terminal report
    counts = {"READY": 0, "BLOCKED": 0, "REVIEW": 0}
    for j in classified:
        counts[j["status"]] += 1

    print(f"Parsed {len(classified)} logical jobs")
    print(f"  READY    : {counts['READY']}")
    print(f"  BLOCKED  : {counts['BLOCKED']}  — {[j['job_id'] for j in classified if j['status']=='BLOCKED']}")
    print(f"  REVIEW   : {counts['REVIEW']}  — {[j['job_id'] for j in classified if j['status']=='REVIEW']}")
    print(f"Wrote {out_path}")
    return 0 if counts["BLOCKED"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
