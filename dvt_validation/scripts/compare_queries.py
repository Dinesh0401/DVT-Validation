#!/usr/bin/env python3
"""
compare_queries.py — Stage 1 preflight step 2: compare the SQL in the
validation contract (duckdb.yaml source.projection) with the SQL that
SeaTunnel actually executes (seatunnel.conf source query / transform).

Normalisation rules applied to both sides before comparison:
  DECIMAL  ↔ NUMERIC
  TEXT     ↔ VARCHAR
  SUBSTR   ↔ SUBSTRING
  SHA256   ↔ STANDARD_HASH(...,'SHA256')
  ||       concatenation (Oracle) ↔ same in PostgreSQL
  quoted identifiers normalised to lower+underscore
  whitespace collapsed

Outputs (generated/):
  query_comparison.json   per-job: {status, duckdb_sql, seatunnel_sql, normalized_are_equal, differences[]}
"""

import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
GENERATED = BASE / "generated"


def normalise(sql: str) -> str:
    if not sql:
        return ""
    s = sql
    # collapse whitespace/newlines
    s = re.sub(r'\s+', ' ', s)
    # DECIMAL ↔ NUMERIC
    s = re.sub(r'\bDECIMAL\b', 'NUMERIC', s, flags=re.I)
    s = re.sub(r'\bNUMERIC\b', 'NUMERIC', s, flags=re.I)
    # TEXT ↔ VARCHAR (both are text families; treat as equivalent)
    s = re.sub(r'\bTEXT\b', 'VARCHAR', s, flags=re.I)
    # SUBSTR ↔ SUBSTRING
    s = re.sub(r'\bSUBSTR\b', 'SUBSTRING', s, flags=re.I)
    # SHA256(expr) ↔ STANDARD_HASH(expr,'SHA256') — strip STANDARD_HASH wrapper
    s = re.sub(r"\bSTANDARD_HASH\s*\(", "SHA256(", s, flags=re.I)
    s = re.sub(r"'SHA256'\)", ")", s, flags=re.I)
    # || concatenation — keep as-is (same semantics)
    # Oracle: FROM "T" AS OF SCN ${run_scn} "t0"
    # Strip the AS OF SCN clause entirely, then the alias "t0" becomes bare t0
    s = re.sub(r'\bAS\s+OF\s+SCN\s+\S+\s*', '', s)
    # quoted identifiers: "FOO" → foo
    s = re.sub(r'"([^"]*)"', lambda m: m.group(1).lower(), s)
    # table alias AS → bare (Oracle doesn't use AS for aliases)
    s = re.sub(r'\bAS\s+(t\d+|s\d+|u\d+|lk\d+|d\d+)\b', r'\1', s, flags=re.I)
    # trailing/leading
    s = s.strip()
    return s


def compare(sql_a: str, sql_b: str) -> dict:
    na, nb = normalise(sql_a), normalise(sql_b)
    equal = na == nb
    diffs = []
    if not equal:
        # line-level diff for readability
        a_lines, b_lines = na.split(' '), nb.split(' ')
        for i, (x, y) in enumerate(zip(a_lines, b_lines)):
            if x != y:
                diffs.append(f"token {i}: '{x}' vs '{y}'")
        if len(a_lines) != len(b_lines):
            diffs.append(f"length: {len(a_lines)} vs {len(b_lines)} tokens")
    return {"equal": equal, "differences": diffs,
            "normalized_a": na, "normalized_b": nb}


def main():
    with open(GENERATED / "jobs.json") as f:
        manifest = json.load(f)

    results = []
    for entry in manifest["jobs"]:
        job_id = entry["job_id"]
        d = entry.get("duckdb") or {}
        s = entry.get("seatunnel") or {}

        duckdb_sql  = d.get("source_projection")
        seat_src    = s.get("source_query")
        seat_trx    = s.get("transform_sql")
        seat_dml    = s.get("dml_statement")

        cmp_src = compare(duckdb_sql or "", seat_src or "") if (duckdb_sql and seat_src) else None
        cmp_trx = compare(duckdb_sql or "", seat_trx or "") if (duckdb_sql and seat_trx) else None

        if cmp_src and cmp_src["equal"]:
            status = "MATCH"
        elif cmp_trx and cmp_trx["equal"]:
            status = "MATCH-via-transform"
        elif entry["status"] == "BLOCKED":
            status = "BLOCKED"
        else:
            status = "REVIEW"

        results.append({
            "job_id": job_id,
            "status": status,
            "source_comparison": cmp_src,
            "transform_comparison": cmp_trx,
            "duckdb_sql": duckdb_sql,
            "seatunnel_source": seat_src,
            "seatunnel_transform": seat_trx,
        })

    out = GENERATED / "query_comparison.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)

    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("Query comparison:")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
