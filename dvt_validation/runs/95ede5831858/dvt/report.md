# DVT Validation Report — Run `95ede5831858`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-08T04:42:33.068460+00:00`

## Summary
- Total Checks: 5
- Passed: 4
- Failed: 1

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (263ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (66ms)

## Migration Job Validations
### Job: `JOB-banking_accounts`
- Source: `banking.ACCOUNTS`
- Target: `public.accounts`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB-banking_accounts_schema`): `[PASSED]` Schema validation passed.
  - Expected: `['open_date', 'customer_id', 'status', 'is_active', 'account_id', 'branch_code', 'balance', 'account_type']` | Actual: `['open_date', 'customer_id', 'status', 'is_active', 'account_id', 'branch_code', 'balance', 'account_type']`
- **row_count** (`JOB-banking_accounts_row_count`): `[PASSED]` Row count matches.
  - Difference: `0`
  - Expected: `2` | Actual: `2`
- **digest** (`JOB-banking_accounts_digest`): `[FAILED]` Data digest mismatch between Oracle source projection and PostgreSQL target.
  - Expected: `474d081c1491cdb36aab089fd000f43d6160e16ca86d1a7af20a62dc32be9695` | Actual: `d88a764e7376b654534a1936eb3704b856a89b0d372e8c44950140433b48b044`

#### Data Discrepancy Breakdown (Exact Differing Records):
**Analysis Summary:** Detected 2 column value discrepancy/discrepancies across shared records.
- **Key Column:** `account_id`
- **Extra Records in Target:** 0
- **Missing Records in Target:** 0

##### Column Value Mismatches on Matched Keys:
| Key | Column | Source Value (Oracle) | Target Value (PostgreSQL) |
| :--- | :--- | :--- | :--- |
| account_id=1001 | `open_date` | `2026-01-01 10:00:00` | `2026-10-07 16:31:34.854577` |
| account_id=1002 | `open_date` | `2026-01-01 10:00:00` | `2026-10-07 16:31:34.854577` |

#### Recommended Remediation (Schema DDL & SQL Query):
*Remediation recommendations generated to align schema and SQL transformation.*

##### 1. Correct Target PostgreSQL Schema (DDL):
```sql
CREATE TABLE IF NOT EXISTS "public"."accounts" (
    "account_id" BIGINT NOT NULL,
    "customer_id" BIGINT,
    "account_type" VARCHAR(30),
    "balance" NUMERIC(12, 2),
    "branch_code" VARCHAR(20),
    "open_date" TIMESTAMP,
    "status" VARCHAR(20),
    "is_active" INTEGER,
    CONSTRAINT "pk_accounts" PRIMARY KEY ("account_id")
);
```

##### 3. Correct Source-to-Target Transformation SQL Query:
```sql
SELECT
  "ACCOUNT_ID" AS "account_id",
  "CUSTOMER_ID" AS "customer_id",
  NULLIF("ACCOUNT_TYPE", '') AS "account_type",
  "BALANCE" AS "balance",
  "OPEN_DATE" AS "open_date",
  NULLIF("STATUS", '') AS "status",
  "IS_ACTIVE" AS "is_active",
  NULLIF("BRANCH_CODE", '') AS "branch_code"
FROM "BANKING"."ACCOUNTS"
```

##### 4. SeaTunnel Transformer Configuration Block:
```hocon
transform {
  Sql {
    source_table_name = "src_accounts"
    result_table_name = "sink_accounts"
    query = "SELECT "ACCOUNT_ID" AS "account_id", "CUSTOMER_ID" AS "customer_id", NULLIF("ACCOUNT_TYPE", '') AS "account_type", "BALANCE" AS "balance", "OPEN_DATE" AS "open_date", NULLIF("STATUS", '') AS "status", "IS_ACTIVE" AS "is_active", NULLIF("BRANCH_CODE", '') AS "branch_code" FROM src_accounts"
  }
}
```

##### Implementation Instructions for Transformer Pipeline:
- 1. To fix target schema: Run 'correct_target_schema_ddl' in PostgreSQL (or execute 'alter_table_ddl' if only missing columns).
- 2. To fix data transformation: Update the transformer Python file or SeaTunnel config with 'correct_transform_query'.
- 3. In SeaTunnel Zeta configuration: Place 'seatunnel_transform_block' inside the job configuration.

