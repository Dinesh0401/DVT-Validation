from app.services.remediation_service import (
    oracle_to_postgres_type,
    infer_postgres_type_from_name,
    generate_target_schema_ddl,
    generate_alter_table_ddl,
    generate_correct_sql_query,
    generate_seatunnel_transform_conf,
    generate_sync_dml,
    build_remediation_bundle,
)
from app.services.db_service import OracleService, PostgresService


def test_oracle_to_postgres_type_mapping():
    assert oracle_to_postgres_type({"type": "NUMBER", "precision": 1, "scale": 0}) == "INTEGER"
    assert oracle_to_postgres_type({"type": "NUMBER", "precision": 12, "scale": 2}) == "NUMERIC(12, 2)"
    assert oracle_to_postgres_type({"type": "NUMBER", "precision": None, "scale": None}) == "BIGINT"
    assert oracle_to_postgres_type({"type": "VARCHAR2", "length": 50}) == "VARCHAR(50)"
    assert oracle_to_postgres_type({"type": "TIMESTAMP(6)"}) == "TIMESTAMP"
    assert oracle_to_postgres_type({"type": "CLOB"}) == "TEXT"
    assert oracle_to_postgres_type({"type": "BLOB"}) == "BYTEA"


def test_infer_postgres_type_from_name():
    assert infer_postgres_type_from_name("account_id") == "BIGINT"
    assert infer_postgres_type_from_name("total_balance") == "NUMERIC(18, 2)"
    assert infer_postgres_type_from_name("is_active") == "INTEGER"
    assert infer_postgres_type_from_name("created_at") == "TIMESTAMP"
    assert infer_postgres_type_from_name("branch_name") == "VARCHAR(255)"


def test_generate_target_schema_ddl():
    cols = [
        {"name": "account_id", "pg_type": "BIGINT", "nullable": False},
        {"name": "balance", "pg_type": "NUMERIC(12, 2)", "nullable": True},
        {"name": "status", "pg_type": "VARCHAR(20)", "nullable": True},
    ]
    ddl = generate_target_schema_ddl("public", "accounts", cols, pk_col="account_id")
    assert 'CREATE TABLE IF NOT EXISTS "public"."accounts"' in ddl
    assert '"account_id" BIGINT NOT NULL' in ddl
    assert '"balance" NUMERIC(12, 2)' in ddl
    assert 'CONSTRAINT "pk_accounts" PRIMARY KEY ("account_id")' in ddl


def test_generate_alter_table_ddl():
    meta = {
        "branch_code": {"name": "branch_code", "pg_type": "VARCHAR(20)"},
        "is_active": {"name": "is_active", "pg_type": "INTEGER"},
    }
    stmts = generate_alter_table_ddl("public", "accounts", ["branch_code", "is_active"], meta)
    assert len(stmts) == 2
    assert 'ALTER TABLE "public"."accounts" ADD COLUMN IF NOT EXISTS "branch_code" VARCHAR(20);' in stmts
    assert 'ALTER TABLE "public"."accounts" ADD COLUMN IF NOT EXISTS "is_active" INTEGER;' in stmts


def test_generate_correct_sql_query():
    cols_meta = {
        "status": {"raw_name": "STATUS", "type": "VARCHAR2"},
        "balance": {"raw_name": "BALANCE", "type": "NUMBER"},
    }
    query = generate_correct_sql_query("banking", "ACCOUNTS", ["status", "balance"], cols_meta)
    assert 'NULLIF("STATUS", \'\') AS "status"' in query
    assert '"BALANCE" AS "balance"' in query
    assert 'FROM "BANKING"."ACCOUNTS"' in query


def test_generate_seatunnel_transform_conf():
    query = 'SELECT "ACCOUNT_ID" AS "account_id" FROM "BANKING"."ACCOUNTS"'
    conf = generate_seatunnel_transform_conf("JOB-1", "ACCOUNTS", "accounts", query)
    assert "transform {" in conf
    assert 'source_table_name = "src_accounts"' in conf
    assert 'result_table_name = "sink_accounts"' in conf
    assert "query = " in conf


def test_generate_sync_dml():
    missing = [{"account_id": 1001, "status": "ACTIVE"}]
    extra = [{"account_id": 1002}]
    dml = generate_sync_dml("public", "accounts", missing, extra, pk_col="account_id")
    assert 'INSERT INTO "public"."accounts"' in dml["insert_missing_sql"]
    assert 'DELETE FROM "public"."accounts"' in dml["delete_extra_sql"]
    assert "'1002'" in dml["delete_extra_sql"]


def test_build_remediation_bundle_live():
    ora = OracleService()
    pg = PostgresService()
    bundle = build_remediation_bundle(
        oracle_svc=ora,
        postgres_svc=pg,
        src_schema="banking",
        src_table="ACCOUNTS",
        tgt_schema="public",
        tgt_table="accounts",
        tgt_cols=["account_id", "customer_id", "balance", "status"],
        job_id="JOB-banking_accounts",
    )
    assert bundle["job_id"] == "JOB-banking_accounts"
    assert "correct_target_schema_ddl" in bundle
    assert "correct_transform_query" in bundle
    assert "seatunnel_transform_block" in bundle
    assert len(bundle["instructions_for_teammate"]) == 3
