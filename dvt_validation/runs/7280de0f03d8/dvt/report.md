# DVT Validation Report — Run `7280de0f03d8`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T11:03:30.950803+00:00`

## Summary
- Total Checks: 4
- Passed: 3
- Failed: 1

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (313ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (101ms)

## Migration Job Validations
### Job: `JOB-banking_accounts`
- Source: `banking.ACCOUNTS`
- Target: `public.accounts`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB-banking_accounts_schema`): `[PASSED]` Schema validation passed.
  - Expected: `['account_type', 'is_active', 'account_id', 'status', 'balance', 'branch_code', 'open_date', 'customer_id']` | Actual: `['account_type', 'is_active', 'account_id', 'status', 'balance', 'branch_code', 'open_date', 'customer_id']`
- **row_count** (`JOB-banking_accounts_row_count`): `[FAILED]` Row count mismatch: source=0 target=2.
  - Difference: `2`
  - Expected: `0` | Actual: `2`
