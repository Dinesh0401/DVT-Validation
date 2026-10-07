# DVT Validation Report — Run `1aa974a2ada1`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T10:21:13.144342+00:00`

## Summary
- Total Checks: 4
- Passed: 3
- Failed: 1

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (312ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (117ms)

## Migration Job Validations
### Job: `JOB-banking_accounts`
- Source: `banking.ACCOUNTS`
- Target: `public.accounts`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB-banking_accounts_schema`): `[FAILED]` Schema validation failed with 1 issues.
  - Expected: `['open_date', 'status', 'balance', 'account_type', 'branch_code', 'account_id', 'is_active', 'customer_id']` | Actual: `Table/Columns verified`
- **row_count** (`JOB-banking_accounts_row_count`): `[PASSED]` Row count matches.
  - Difference: `0`
  - Expected: `0` | Actual: `0`
