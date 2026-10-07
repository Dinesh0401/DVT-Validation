# DVT Validation Report — Run `ffbe6fb1d526`

**Overall Result:** `FAILED`
**Timestamp:** `2026-10-07T13:00:31.685944+00:00`

## Summary
- Total Checks: 5
- Passed: 3
- Failed: 2

## Connectivity Checks
- **oracle_connectivity**: `[PASSED]` Successfully connected to Oracle at localhost:1521/FREEPDB1 (314ms)
- **postgres_connectivity**: `[PASSED]` Successfully connected to PostgreSQL at localhost:5432/migration_exercise (86ms)

## Migration Job Validations
### Job: `JOB-banking_accounts`
- Source: `banking.ACCOUNTS`
- Target: `public.accounts`
- Status: `FAILED`

#### Checks:
- **schema** (`JOB-banking_accounts_schema`): `[PASSED]` Schema validation passed.
  - Expected: `['is_active', 'branch_code', 'open_date', 'customer_id', 'status', 'account_id', 'account_type', 'balance']` | Actual: `['is_active', 'branch_code', 'open_date', 'customer_id', 'status', 'account_id', 'account_type', 'balance']`
- **row_count** (`JOB-banking_accounts_row_count`): `[FAILED]` Row count query error: Oracle query error: ORA-00907: missing right parenthesis
Help: https://docs.oracle.com/error-help/db/ora-00907/
  - Expected: `Row count query execution` | Actual: `Oracle query error: ORA-00907: missing right parenthesis
Help: https://docs.oracle.com/error-help/db/ora-00907/`
- **digest** (`JOB-banking_accounts_digest`): `[FAILED]` Digest calculation error: Oracle query error: ORA-00907: missing right parenthesis
Help: https://docs.oracle.com/error-help/db/ora-00907/
  - Expected: `SHA-256 digest computation` | Actual: `Oracle query error: ORA-00907: missing right parenthesis
Help: https://docs.oracle.com/error-help/db/ora-00907/`
