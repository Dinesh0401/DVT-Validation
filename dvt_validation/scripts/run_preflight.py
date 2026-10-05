#!/usr/bin/env python3
"""
run_preflight.py — Stage 1 preflight orchestrator (no DB access, no data).

Runs the 3 sub-steps in order:
  1 extract_jobs.py        — parse inputs → generated/jobs.json
  2 compare_queries.py     — SQL comparison → generated/query_comparison.json
  3 build_dvt_config.py    — DVT YAML skeleton → generated/dvt_validation_config.yaml

Exit codes:
  0  READY    — all jobs classified READY, queries matched
  1  BLOCKED  — hard stop (missing job, missing query)
  2  REVIEW   — pass with warnings (orphan/referential, or query mismatches)
"""

import json, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
GENERATED = BASE / "generated"


def run_step(name: str) -> int:
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print('='*60)
    result = subprocess.run([sys.executable, str(BASE / "scripts" / f"{name}.py")])
    return result.returncode


def main():
    GENERATED.mkdir(parents=True, exist_ok=True)

    # Step 1 — parse
    if run_step("extract_jobs") != 0:
        print("FATAL: extract_jobs failed — aborting preflight")
        return 1

    # Step 2 — compare
    run_step("compare_queries")

    # Step 3 — build DVT skeleton
    run_step("build_dvt_config")

    # Summarize
    with open(GENERATED / "jobs.json") as f:
        manifest = json.load(f)

    jobs = manifest["jobs"]
    ready    = [j for j in jobs if j["status"] == "READY"]
    blocked  = [j for j in jobs if j["status"] == "BLOCKED"]
    review   = [j for j in jobs if j["status"] == "REVIEW"]

    print(f"\n{'='*60}")
    print("STAGE-1 PREFLIGHT SUMMARY")
    print('='*60)
    print(f"Total logical jobs : {len(jobs)}")
    print(f"READY              : {len(ready)}")
    print(f"BLOCKED (hard stop): {len(blocked)}")
    for j in blocked:
        print(f"    {j['job_id']}: {j['reason']}")
    print(f"REVIEW (warning)   : {len(review)}")
    for j in review:
        print(f"    {j['job_id']}: {j['reason']}")

    # Query comparison summary
    qc_path = GENERATED / "query_comparison.json"
    if qc_path.exists():
        with open(qc_path) as f:
            qc = json.load(f)
        match = [r for r in qc if r["status"] == "MATCH"]
        mismatch = [r for r in qc if r["status"] not in ("MATCH", "MATCH-via-transform")]
        print(f"\nQuery comparison: {len(match)} matched, {len(mismatch)} mismatched/blocked")
        for r in mismatch:
            print(f"    {r['job_id']}: {r['status']}")

    if blocked:
        print("\nResult: BLOCKED — resolve blockers before migration")
        return 1
    if review:
        print("\nResult: REVIEW — proceed with caution; see warnings above")
        return 2
    print("\nResult: READY — Stage-1 validation complete, proceed to Stage-2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
