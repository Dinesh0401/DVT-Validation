# Stage-1 Pre-migration Preflight Verification

**Purpose:** Validate the migration contract (`duckdb.yaml`) and migration execution plan (`seatunnel.conf`) *before* any data moves or database is touched.

Stage-1 is a static, zero-DB-access contract-vs-plan verification pipeline.

---

## Architecture & Layers

```
Stage-1 Preflight Verification Pipeline
  │
  ├── Layer 1: Structural Integrity (YAML & HOCON Syntax, Brace Balancing)
  ├── Layer 2: Relation & Entity Mapping (Oracle Source ↔ Postgres Target)
  ├── Layer 3: Snapshot SCN Binding Verification (AS OF SCN ${run_scn})
  ├── Layer 4: Semantic Query Equivalence (Dialect Translation & Expression Audit)
  ├── Layer 5: Target DDL & Schema Consistency (DDL Types, Nullability, Columns)
  └── Layer 6: DVT Execution Readiness (Validation Plan, CLI Scripts, Configs)
```

---

## Project Structure

```
dvt_validation/
  input/
    duckdb.yaml              # Validation contract (11 active jobs, 1 blocked, 106 checks)
    seatunnel.conf           # Migration execution plan (22 SeaTunnel Zeta jobs: ddl + data)
  generated/
    jobs.json                # Verified manifest of all 12 logical jobs with complete metadata
    query_comparison.json    # Snapshot SCN audit, dialect notes, and semantic token comparison
    dvt_validation_plan.yaml # Stage-1 Intermediate Representation / DVT Validation Plan
    dvt_cli_commands.sh      # Executable Google Cloud DVT CLI bash script (--dry-run supported)
    dvt_cli_commands.bat     # Executable Windows batch script (--dry-run supported)
    dvt_configs/             # 22 Native DVT-compliant YAML configs (schema & row validations)
  scripts/
    extract_jobs.py          # HOCON/YAML parser & 3D relation matcher
    compare_queries.py       # SCN binding verifier & semantic dialect analyzer
    build_dvt_config.py      # Generates DVT plan, CLI commands, and native configs
    run_preflight.py         # End-to-end pipeline orchestrator & report generator
  reports/
    stage1_preflight_report.md # Executive evidence report with verification matrix
```

---

## Running the Preflight

Execute the complete preflight pipeline:

```bash
python dvt_validation/scripts/run_preflight.py
```

### Exit Codes:
- `0` (**READY**)   : 100% aligned, no blockers, no unresolved review items.
- `1` (**BLOCKED**) : Hard stop (e.g. `JOB-shop_order_line` is unresolved, or structural failure).
- `2` (**REVIEW**)  : Functional with warnings (e.g. dialect review notes require human sign-off).

---

## Key Verification Results

1. **Job Scope:**
   - Total Logical Jobs: **12**
   - Active & Fully Paired: **11**
   - Explicitly Blocked: **1** (`JOB-shop_order_line` — missing query in specification)
2. **Snapshot SCN Binding:**
   - 11/11 active SeaTunnel queries enforce `AS OF SCN ${run_scn}` on every Oracle table read.
3. **Target Schema Alignment:**
   - 11/11 target PostgreSQL DDL tables match SeaTunnel DML insert columns and DuckDB projections 100%.
4. **Dialect Nuances:**
   - `JOB-shop_customer`: Oracle `CHAR(2)` blank-padding vs DuckDB `TEXT(2)`.
   - `JOB-shop_price_history`: Oracle `DESC` native `NULLS FIRST` vs DuckDB explicit `NULLS FIRST`.
