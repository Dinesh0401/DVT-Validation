# DVT Validation Report — Run `5685abff011f`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T12:59:27.582893+00:00`

## Summary
- Total Checks: 4
- Passed: 2
- Failed: 2

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (256ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (91ms)

## Migration Job Validations
### Job: `JOB_EMPLOYEES_DVT`
- Source: `public.EMPLOYEES`
- Target: `public.employees`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB_EMPLOYEES_DVT_schema`): `[FAILED]` Schema validation failed with 2 issues.
  - Expected: `['emp_id', 'first_name', 'salary']` | Actual: `['employee_id', 'first_name', 'salary']`
- **row_count** (`JOB_EMPLOYEES_DVT_row_count`): `[FAILED]` Row count query error: Oracle query error: ORA-00942: table or view "public"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/
  - Expected: `Row count query execution` | Actual: `Oracle query error: ORA-00942: table or view "public"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/`
