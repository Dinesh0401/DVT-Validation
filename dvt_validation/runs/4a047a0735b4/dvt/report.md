# DVT Validation Report — Run `4a047a0735b4`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T13:04:31.149280+00:00`

## Summary
- Total Checks: 4
- Passed: 2
- Failed: 2

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (279ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (85ms)

## Migration Job Validations
### Job: `JOB_EMPLOYEES_DVT`
- Source: `public.EMPLOYEES`
- Target: `public.employees`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB_EMPLOYEES_DVT_schema`): `[FAILED]` Schema validation failed with 2 issues.
  - Expected: `['first_name', 'emp_id', 'salary']` | Actual: `['first_name', 'employee_id', 'salary']`
- **row_count** (`JOB_EMPLOYEES_DVT_row_count`): `[FAILED]` Row count query error: Oracle query error: ORA-00942: table or view "PUBLIC"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/
  - Expected: `Row count query execution` | Actual: `Oracle query error: ORA-00942: table or view "PUBLIC"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/`
