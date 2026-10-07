# DVT Validation Report — Run `b9cb5ca917c5`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T16:08:01.751856+00:00`

## Summary
- Total Checks: 4
- Passed: 2
- Failed: 2

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (222ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (69ms)

## Migration Job Validations
### Job: `JOB_EMPLOYEES_DVT`
- Source: `public.EMPLOYEES`
- Target: `public.employees`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB_EMPLOYEES_DVT_schema`): `[FAILED]` Schema validation failed with 2 issues.
  - Expected: `['first_name', 'salary', 'emp_id']` | Actual: `['employee_id', 'first_name', 'salary']`
  - Problem: `MISSING_COLUMN` - Column missing in PostgreSQL target table
  - Problem: `EXTRA_COLUMN` - Column 'employee_id' exists in PostgreSQL target but not in contract
- **row_count** (`JOB_EMPLOYEES_DVT_row_count`): `[FAILED]` Row count query error: Oracle query error: ORA-00942: table or view "PUBLIC"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/
  - Expected: `Row count query execution` | Actual: `Oracle query error: ORA-00942: table or view "PUBLIC"."EMPLOYEES" does not exist
Help: https://docs.oracle.com/error-help/db/ora-00942/`

#### Recommended Remediation (Schema DDL & SQL Query):
*Remediation recommendations generated to align schema and SQL transformation.*

##### 1. Correct Target PostgreSQL Schema (DDL):
```sql
CREATE TABLE IF NOT EXISTS "public"."employees" (
    "emp_id" BIGINT,
    "first_name" VARCHAR(255),
    "salary" NUMERIC(18, 2),
    CONSTRAINT "pk_employees" PRIMARY KEY ("employee_id")
);
```

##### 2. Missing Columns Alter Statements:
```sql
ALTER TABLE "public"."employees" ADD COLUMN IF NOT EXISTS "emp_id" BIGINT;
```

##### 3. Correct Source-to-Target Transformation SQL Query:
```sql
SELECT
  NULLIF("EMP_ID", '') AS "emp_id",
  NULLIF("FIRST_NAME", '') AS "first_name",
  NULLIF("SALARY", '') AS "salary"
FROM "PUBLIC"."EMPLOYEES"
```

##### 4. SeaTunnel Transformer Configuration Block:
```hocon
transform {
  Sql {
    source_table_name = "src_employees"
    result_table_name = "sink_employees"
    query = "SELECT NULLIF("EMP_ID", '') AS "emp_id", NULLIF("FIRST_NAME", '') AS "first_name", NULLIF("SALARY", '') AS "salary" FROM src_employees"
  }
}
```

##### Implementation Instructions for Transformer Pipeline:
- 1. To fix target schema: Run 'correct_target_schema_ddl' in PostgreSQL (or execute 'alter_table_ddl' if only missing columns).
- 2. To fix data transformation: Update the transformer Python file or SeaTunnel config with 'correct_transform_query'.
- 3. In SeaTunnel Zeta configuration: Place 'seatunnel_transform_block' inside the job configuration.

