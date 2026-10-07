# DVT Validation Report — Run `d19724c775af`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T15:58:39.048570+00:00`

## Summary
- Total Checks: 4
- Passed: 2
- Failed: 2

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (223ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (74ms)

## Migration Job Validations
### Job: `JOB_EMPLOYEES_DVT`
- Source: `public.EMPLOYEES`
- Target: `public.employees`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB_EMPLOYEES_DVT_schema`): `[FAILED]` Schema validation failed with 2 issues.
  - Expected: `['salary', 'emp_id', 'first_name']` | Actual: `['salary', 'first_name', 'employee_id']`
  - Problem: `MISSING_COLUMN` - Column missing in PostgreSQL target table
  - Problem: `EXTRA_COLUMN` - Column 'employee_id' exists in PostgreSQL target but not in contract
- **row_count** (`JOB_EMPLOYEES_DVT_row_count`): `[FAILED]` Row count query error: Oracle query error: ORA-00942: table or view "PUBLIC"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/
  - Expected: `Row count query execution` | Actual: `Oracle query error: ORA-00942: table or view "PUBLIC"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/`
