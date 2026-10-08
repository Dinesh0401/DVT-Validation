"""
Remediation Service — Generate corrective SQL queries, target schema DDL, and SeaTunnel configurations.

Empowers developers and pipeline transformers by automatically producing:
  1. Correct Target PostgreSQL Schema DDL (CREATE TABLE / ALTER TABLE)
  2. Correct Source Transformation / Projection SQL Query
  3. SeaTunnel HOCON Transform Block for the transformer Python engine
  4. Data Synchronization DML (INSERT missing records / DELETE extra records)

Zero hardcoding — operates dynamically on any table, schema, and column metadata.
"""
from __future__ import annotations

import re
from typing import Any

from app.services.db_service import OracleService, PostgresService


def infer_postgres_type_from_name(col_name: str) -> str:
    """Infer a PostgreSQL data type from a column name when DB metadata is unavailable."""
    c = col_name.lower().strip()
    if c == "id" or c.endswith("_id") or c.startswith("id_"):
        return "BIGINT"
    if any(k in c for k in ("price", "amount", "balance", "cost", "total", "tax", "discount", "rate", "fee", "salary")):
        return "NUMERIC(18, 2)"
    if any(k in c for k in ("qty", "quantity", "count", "num", "age", "year", "month", "level", "rank")):
        return "INTEGER"
    if any(k in c for k in ("date", "time", "created_at", "updated_at", "timestamp")):
        return "TIMESTAMP"
    if any(k in c for k in ("is_", "has_", "flag", "active", "enabled")):
        return "INTEGER"
    if any(k in c for k in ("description", "details", "notes", "payload", "comment", "body")):
        return "TEXT"
    return "VARCHAR(255)"


def oracle_to_postgres_type(col_meta: dict[str, Any]) -> str:
    """Map Oracle column metadata to canonical PostgreSQL data type."""
    data_type = str(col_meta.get("type", "")).upper().strip()
    precision = col_meta.get("precision")
    scale = col_meta.get("scale")
    length = col_meta.get("length")

    if "NUMBER" in data_type:
        if precision == 1 and scale == 0:
            return "INTEGER"
        if scale is not None and scale > 0:
            prec = precision or 18
            return f"NUMERIC({prec}, {scale})"
        if precision is None and scale is None:
            return "BIGINT"
        if precision is not None and precision <= 4:
            return "SMALLINT"
        if precision is not None and precision <= 9:
            return "INTEGER"
        return "BIGINT"

    if any(k in data_type for k in ("VARCHAR2", "NVARCHAR2", "CHAR", "NCHAR")):
        if length and length > 0:
            return f"VARCHAR({length})"
        return "VARCHAR(255)"

    if any(k in data_type for k in ("TIMESTAMP", "DATE")):
        return "TIMESTAMP"

    if any(k in data_type for k in ("CLOB", "NCLOB", "LONG")):
        return "TEXT"

    if any(k in data_type for k in ("BLOB", "RAW")):
        return "BYTEA"

    if any(k in data_type for k in ("FLOAT", "DOUBLE", "BINARY_DOUBLE")):
        return "DOUBLE PRECISION"

    return infer_postgres_type_from_name(col_meta.get("name", ""))


def generate_target_schema_ddl(
    target_schema: str,
    target_table: str,
    columns_meta: list[dict[str, Any]],
    pk_col: str | None = None,
) -> str:
    """
    Generate PostgreSQL CREATE TABLE DDL matching source column specifications.
    """
    lines = [f'CREATE TABLE IF NOT EXISTS "{target_schema}"."{target_table}" (']
    col_defs: list[str] = []

    for col in columns_meta:
        c_name = col.get("name", "").lower()
        pg_type = col.get("pg_type") or oracle_to_postgres_type(col)
        nullable_clause = ""
        if not col.get("nullable", True) or (pk_col and c_name == pk_col.lower()):
            nullable_clause = " NOT NULL"
        col_defs.append(f'    "{c_name}" {pg_type}{nullable_clause}')

    if pk_col:
        clean_pk = pk_col.lower()
        col_defs.append(f'    CONSTRAINT "pk_{target_table}" PRIMARY KEY ("{clean_pk}")')

    lines.append(",\n".join(col_defs))
    lines.append(");")
    return "\n".join(lines)


def generate_alter_table_ddl(
    target_schema: str,
    target_table: str,
    missing_columns: list[str],
    columns_meta_dict: dict[str, dict[str, Any]],
) -> list[str]:
    """
    Generate ALTER TABLE statements for any missing columns on PostgreSQL target.
    """
    alter_stmts: list[str] = []
    for m in missing_columns:
        m_low = m.lower()
        col_meta = columns_meta_dict.get(m_low, {"name": m_low})
        pg_type = col_meta.get("pg_type") or oracle_to_postgres_type(col_meta)
        alter_stmts.append(
            f'ALTER TABLE "{target_schema}"."{target_table}" ADD COLUMN IF NOT EXISTS "{m_low}" {pg_type};'
        )
    return alter_stmts


def generate_correct_sql_query(
    source_schema: str | None,
    source_table: str,
    target_columns: list[str],
    source_columns_meta: dict[str, dict[str, Any]],
) -> str:
    """
    Generate correct Oracle-to-PostgreSQL SQL transformation projection query.
    Applies NULLIF for empty string normalization and preserves column mappings.
    """
    projections: list[str] = []

    for t_col in target_columns:
        t_low = t_col.lower()
        src_meta = source_columns_meta.get(t_low)
        raw_name = src_meta.get("raw_name", t_col.upper()) if src_meta else t_col.upper()
        col_type = src_meta.get("type", "") if src_meta else ""

        if any(k in col_type for k in ("VARCHAR", "CHAR")):
            projections.append(f'  NULLIF("{raw_name}", \'\') AS "{t_low}"')
        else:
            projections.append(f'  "{raw_name}" AS "{t_low}"')

    schema_prefix = f'"{source_schema.upper()}".' if source_schema else ""
    query = (
        "SELECT\n"
        + ",\n".join(projections)
        + f'\nFROM {schema_prefix}"{source_table.upper()}"'
    )
    return query


def generate_seatunnel_transform_conf(
    job_id: str,
    source_table: str,
    target_table: str,
    query: str,
) -> str:
    """
    Generate SeaTunnel HOCON transform block for the transformer engine.
    """
    clean_tgt = re.sub(r"[^a-zA-Z0-9_]", "_", target_table).lower()

    # Form clean query without escaped quotes for SeaTunnel SQL transform
    clean_q = re.sub(r'FROM\s+["`]?\w+["`]?\.["`]?\w+["`]?', f"FROM src_{clean_tgt}", query, flags=re.IGNORECASE)
    clean_q = clean_q.replace('"', "")  # Strip internal double quotes for clean HOCON formatting

    conf = f"""transform {{
  Sql {{
    source_table_name = "src_{clean_tgt}"
    result_table_name = "sink_{clean_tgt}"
    query = "{' '.join(clean_q.split())}"
  }}
}}"""
    return conf


def generate_sync_dml(
    target_schema: str,
    target_table: str,
    missing_records: list[dict[str, Any]],
    extra_records: list[dict[str, Any]],
    pk_col: str | None = None,
) -> dict[str, Any]:
    """
    Generate DML sync queries to reconcile data differences.
    """
    res: dict[str, Any] = {
        "insert_missing_sql": None,
        "delete_extra_sql": None,
    }

    if missing_records:
        insert_stmts = []
        for r in missing_records[:10]:
            cols = [f'"{k}"' for k in r.keys()]
            vals = []
            for v in r.values():
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    v_str = str(v).replace("'", "''")
                    vals.append(f"'{v_str}'")
            insert_stmts.append(
                f'INSERT INTO "{target_schema}"."{target_table}" ({", ".join(cols)}) VALUES ({", ".join(vals)});'
            )
        res["insert_missing_sql"] = "\n".join(insert_stmts)

    if extra_records and pk_col:
        keys = [str(r[pk_col]) for r in extra_records if pk_col in r and r[pk_col] is not None]
        if keys:
            formatted_keys = ", ".join(f"'{k}'" for k in keys[:20])
            res["delete_extra_sql"] = (
                f'DELETE FROM "{target_schema}"."{target_table}" WHERE "{pk_col}" IN ({formatted_keys});'
            )

    return res


def build_remediation_bundle(
    oracle_svc: OracleService,
    postgres_svc: PostgresService,
    src_schema: str | None,
    src_table: str,
    tgt_schema: str | None,
    tgt_table: str,
    tgt_cols: list[str],
    job_id: str,
    problems: list[dict[str, Any]] | None = None,
    discrepancy_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the complete remediation bundle containing correct SQL query and schema DDL.
    """
    t_schema = tgt_schema or "public"
    pk_col = postgres_svc.fetch_primary_key(t_schema, tgt_table)
    if not pk_col:
        id_cols = [c.lower() for c in tgt_cols if "id" in c.lower()]
        pk_col = id_cols[0] if id_cols else (tgt_cols[0].lower() if tgt_cols else None)

    # 1. Fetch live column metadata from Oracle
    ora_meta_list = oracle_svc.fetch_column_metadata(src_schema, src_table)
    ora_meta_dict = {c["name"].lower(): c for c in ora_meta_list}

    # If Oracle metadata unavailable, construct synthetic metadata from target columns
    if not ora_meta_list:
        ora_meta_list = [
            {
                "name": c.lower(),
                "raw_name": c.upper(),
                "type": "VARCHAR2",
                "length": 255,
                "precision": None,
                "scale": None,
                "nullable": True,
                "pg_type": infer_postgres_type_from_name(c),
            }
            for c in tgt_cols
        ]
        ora_meta_dict = {c["name"].lower(): c for c in ora_meta_list}

    # 2. Generate correct PostgreSQL DDL
    correct_ddl = generate_target_schema_ddl(t_schema, tgt_table, ora_meta_list, pk_col=pk_col)

    # 3. Detect missing columns from problems
    missing_cols: list[str] = []
    if problems:
        for p in problems:
            if p.get("type") == "MISSING_COLUMN" and p.get("expected"):
                missing_cols.append(str(p.get("expected")).lower())

    alter_stmts = generate_alter_table_ddl(t_schema, tgt_table, missing_cols, ora_meta_dict) if missing_cols else []

    # 4. Generate correct transformation query
    correct_query = generate_correct_sql_query(src_schema, src_table, tgt_cols, ora_meta_dict)

    # 5. Generate SeaTunnel transform configuration block
    seatunnel_conf = generate_seatunnel_transform_conf(job_id, src_table, tgt_table, correct_query)

    # 6. Generate data sync DML if discrepancy exists
    dml_sync = {}
    if discrepancy_details:
        dml_sync = generate_sync_dml(
            target_schema=t_schema,
            target_table=tgt_table,
            missing_records=discrepancy_details.get("missing_in_target_records", []),
            extra_records=discrepancy_details.get("extra_in_target_records", []),
            pk_col=pk_col,
        )

    return {
        "job_id": job_id,
        "target_table": f"{t_schema}.{tgt_table}",
        "summary": "Remediation recommendations generated to align schema and SQL transformation.",
        "correct_target_schema_ddl": correct_ddl,
        "alter_table_ddl": alter_stmts,
        "correct_transform_query": correct_query,
        "seatunnel_transform_block": seatunnel_conf,
        "data_sync_dml": dml_sync,
        "instructions_for_teammate": [
            f"1. To fix target schema: Run 'correct_target_schema_ddl' in PostgreSQL (or execute 'alter_table_ddl' if only missing columns).",
            f"2. To fix data transformation: Update the transformer Python file or SeaTunnel config with 'correct_transform_query'.",
            f"3. In SeaTunnel Zeta configuration: Place 'seatunnel_transform_block' inside the job configuration.",
        ],
    }
