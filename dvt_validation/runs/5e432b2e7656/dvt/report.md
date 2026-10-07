# DVT Validation Report — Run `5e432b2e7656`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-06T11:42:54.843812+00:00`

## Summary
- Total Checks: 4
- Passed: 2
- Failed: 2

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (266ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (71ms)

## Migration Job Validations
### Job: `JOB_EMPLOYEES_DVT`
- Source: `public.EMPLOYEES`
- Target: `public.employees`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB_EMPLOYEES_DVT_schema`): `[FAILED]` Schema validation failed with 2 issues.
  - Expected: `['first_name', 'salary', 'emp_id']` | Actual: `['first_name', 'salary', 'employee_id']`
- **row_count** (`JOB_EMPLOYEES_DVT_row_count`): `[FAILED]` Row count mismatch: source=0 target=2.
  - Difference: `2`
  - Expected: `0` | Actual: `2`
