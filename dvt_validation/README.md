# DVT Stage-1 Pre-migration Preflight

**Purpose:** Validate the migration contract and execution plan *before* any data moves.  
**Stage-1** = no DB access, no DuckDB, no actual data validation.

## Project layout

```
dvt_validation/
  input/           duckdb.yaml, seatunnel.conf      (provided, not modified)
  generated/       jobs.json, query_comparison.json, dvt_validation_config.yaml
  scripts/         extract_jobs.py, compare_queries.py, build_dvt_config.py, run_preflight.py
  reports/         (reserved for Stage-2 evidence)
```

## The 3 sub-steps

1. **extract_jobs** — parse both files → `generated/jobs.json`
2. **compare_queries** — normalise + compare SQL → `generated/query_comparison.json`
3. **build_dvt_config** — emit DVT YAML skeleton → `generated/dvt_validation_config.yaml`

Orchestrated by `scripts/run_preflight.py` (exit codes 0=READY, 1=BLOCKED, 2=REVIEW).

## Running

```bash
python3 scripts/run_preflight.py
```

## Normalisation rules (compare_queries.py)

DECIMAL↔NUMERIC, TEXT↔VARCHAR, SUBSTR↔SUBSTRING, SHA256↔STANDARD_HASH,
quoted identifiers lowercased, whitespace collapsed, AS OF SCN stripped.
