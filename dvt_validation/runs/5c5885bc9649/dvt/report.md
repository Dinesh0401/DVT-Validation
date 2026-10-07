# DVT Validation Report — Run `5c5885bc9649`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T13:03:26.928585+00:00`

## Summary
- Total Checks: 5
- Passed: 4
- Failed: 1

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (282ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (90ms)

## Migration Job Validations
### Job: `JOB-banking_accounts`
- Source: `banking.ACCOUNTS`
- Target: `public.accounts`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB-banking_accounts_schema`): `[PASSED]` Schema validation passed.
  - Expected: `['status', 'is_active', 'account_type', 'customer_id', 'branch_code', 'balance', 'open_date', 'account_id']` | Actual: `['status', 'is_active', 'open_date', 'account_type', 'customer_id', 'branch_code', 'balance', 'account_id']`
- **row_count** (`JOB-banking_accounts_row_count`): `[PASSED]` Row count matches.
  - Difference: `0`
  - Expected: `2` | Actual: `2`
- **digest** (`JOB-banking_accounts_digest`): `[FAILED]` Data digest mismatch between Oracle source projection and PostgreSQL target.
  - Expected: `474d081c1491cdb36aab089fd000f43d6160e16ca86d1a7af20a62dc32be9695` | Actual: `d88a764e7376b654534a1936eb3704b856a89b0d372e8c44950140433b48b044`
