-- Remediation Script for JOB_EMPLOYEES_DVT (public.employees)
-- Generated: 2026-10-07T16:09:11.416503+00:00

-- 1. Correct Target PostgreSQL Schema (DDL):
CREATE TABLE IF NOT EXISTS "public"."employees" (
    "emp_id" BIGINT,
    "first_name" VARCHAR(255),
    "salary" NUMERIC(18, 2),
    CONSTRAINT "pk_employees" PRIMARY KEY ("employee_id")
);

-- 2. Missing Columns Alter Statements:
ALTER TABLE "public"."employees" ADD COLUMN IF NOT EXISTS "emp_id" BIGINT;

-- 3. Correct Source-to-Target Transformation Query:
SELECT
  NULLIF("EMP_ID", '') AS "emp_id",
  NULLIF("FIRST_NAME", '') AS "first_name",
  NULLIF("SALARY", '') AS "salary"
FROM "PUBLIC"."EMPLOYEES";
