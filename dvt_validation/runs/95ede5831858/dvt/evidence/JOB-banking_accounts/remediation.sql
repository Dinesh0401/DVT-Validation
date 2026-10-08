-- Remediation Script for JOB-banking_accounts (public.accounts)
-- Generated: 2026-10-08T04:42:33.064979+00:00

-- 1. Correct Target PostgreSQL Schema (DDL):
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

-- 3. Correct Source-to-Target Transformation Query:
SELECT
  "ACCOUNT_ID" AS "account_id",
  "CUSTOMER_ID" AS "customer_id",
  NULLIF("ACCOUNT_TYPE", '') AS "account_type",
  "BALANCE" AS "balance",
  "OPEN_DATE" AS "open_date",
  NULLIF("STATUS", '') AS "status",
  "IS_ACTIVE" AS "is_active",
  NULLIF("BRANCH_CODE", '') AS "branch_code"
FROM "BANKING"."ACCOUNTS";
