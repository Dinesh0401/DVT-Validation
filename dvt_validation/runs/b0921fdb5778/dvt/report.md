# DVT Validation Report — Run `b0921fdb5778`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T15:58:16.265971+00:00`

## Summary
- Total Checks: 5
- Passed: 3
- Failed: 2

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (423ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (48ms)

## Migration Job Validations
### Job: `JOB-banking_accounts`
- Source: `banking.ACCOUNTS`
- Target: `public.accounts`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB-banking_accounts_schema`): `[PASSED]` Schema validation passed.
  - Expected: `['account_id', 'branch_code', 'customer_id', 'balance', 'account_type', 'status', 'open_date', 'is_active']` | Actual: `['account_id', 'branch_code', 'customer_id', 'balance', 'account_type', 'status', 'open_date', 'is_active']`
- **row_count** (`JOB-banking_accounts_row_count`): `[FAILED]` Row count mismatch: source=2 target=4.
  - Difference: `2`
  - Expected: `2` | Actual: `4`
- **digest** (`JOB-banking_accounts_digest`): `[FAILED]` Data digest mismatch between Oracle source projection and PostgreSQL target.
  - Expected: `474d081c1491cdb36aab089fd000f43d6160e16ca86d1a7af20a62dc32be9695` | Actual: `13d44e0521f5144f0cde34f7dcf40147f295d75105a9e43a5e24c77c11c34bb5`

#### Data Discrepancy Breakdown (Exact Differing Records):
**Analysis Summary:** Target (PostgreSQL) has 2 extra record(s) not found in Source (Oracle) [Keys: 1003, 1004]. Detected 2 column value discrepancy/discrepancies across shared records.
- **Key Column:** `account_id`
- **Extra Records in Target:** 2
- **Missing Records in Target:** 0

##### Extra Records in Target (PostgreSQL):
| account_id | customer_id | account_type | balance | branch_code | open_date | status | is_active |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1003 | 103 | SAVINGS | 3500.00 | BR-02 | 2026-02-15 09:30:00 | ACTIVE | 1 |
| 1004 | 104 | CHECKING | 8900.50 | BR-03 | 2026-03-01 14:15:00 | PENDING | 1 |

##### Column Value Mismatches on Matched Keys:
| Key | Column | Source Value (Oracle) | Target Value (PostgreSQL) |
| :--- | :--- | :--- | :--- |
| account_id=1001 | `open_date` | `2026-01-01 10:00:00` | `2026-10-07 16:31:34.854577` |
| account_id=1002 | `open_date` | `2026-01-01 10:00:00` | `2026-10-07 16:31:34.854577` |
