"""
Database Connection Services — generic, reusable Oracle & Postgres services.

Responsibilities:
    • OracleService: connection testing, row count, aggregate, digest calculation
    • PostgresService: schema inspection, column verification, row count, digest calculation
    • Safe credential handling: never exposes passwords in logs, errors, or evidence

Zero business logic hardcoding — all operations work generically for any table/schema.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Any

from app.config import settings


class BaseDbService:
    """Base class for database operations with safe error handling."""

    def sanitize_error(self, err: Exception) -> str:
        """Strip password and sensitive connection details from error message."""
        msg = str(err)
        for secret in (settings.ORACLE_PASSWORD, settings.POSTGRES_PASSWORD):
            if secret and secret in msg:
                msg = msg.replace(secret, "******")
        return msg


class OracleService(BaseDbService):
    """Oracle database access service."""

    def __init__(
        self,
        user: str = settings.ORACLE_USER,
        password: str = settings.ORACLE_PASSWORD,
        host: str = settings.ORACLE_HOST,
        port: str = settings.ORACLE_PORT,
        service_name: str = settings.ORACLE_SERVICE,
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.service_name = service_name

    def test_connection(self) -> tuple[bool, str]:
        """Test Oracle database connectivity without exposing credentials."""
        try:
            # Try importing oracledb or sqlalchemy connection
            import oracledb
            dsn = f"{self.host}:{self.port}/{self.service_name}"
            conn = oracledb.connect(user=self.user, password=self.password, dsn=dsn)
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                cursor.fetchone()
            return True, f"Successfully connected to Oracle at {self.host}:{self.port}/{self.service_name}"
        except Exception as exc:
            return False, f"Oracle Connection Error: {self.sanitize_error(exc)}"

    def _adapt_oracle_sql(self, sql: str | None) -> str | None:
        """Adapt transpiled SQL for Oracle dialect (remove AS before table aliases, normalize relation casing)."""
        if not sql:
            return sql
        # 1. Remove 'AS' before table aliases in FROM/JOIN clauses (Oracle doesn't allow 'FROM table AS alias')
        adapted = re.sub(r'(\b(?:FROM|JOIN)\s+[^\s]+)\s+AS\s+([a-zA-Z0-9_"]+)', r'\1 \2', sql, flags=re.IGNORECASE)
        # 2. Normalize quoted lowercase schema.table to uppercase Oracle identifiers: "schema"."table" -> SCHEMA.TABLE
        adapted = re.sub(r'"([a-zA-Z0-9_]+)"\."([a-zA-Z0-9_]+)"', lambda m: f'{m.group(1).upper()}.{m.group(2).upper()}', adapted)
        return adapted

    def fetch_row_count(self, projection_sql: str | None, table_name: str | None, schema_name: str | None) -> int:
        """Fetch projected source row count from Oracle."""
        adapted_sql = self._adapt_oracle_sql(projection_sql)
        if adapted_sql:
            # Wrap projection query in count
            count_sql = f"SELECT COUNT(*) FROM ({adapted_sql})"
        elif schema_name and table_name:
            count_sql = f'SELECT COUNT(*) FROM "{schema_name.upper()}"."{table_name.upper()}"'
        elif table_name:
            count_sql = f'SELECT COUNT(*) FROM "{table_name.upper()}"'
        else:
            raise ValueError("Insufficient relation metadata for Oracle row count query.")

        return self._execute_scalar_int(count_sql)

    def fetch_aggregate(self, metric_expr: str, projection_sql: str | None, table_name: str | None, schema_name: str | None) -> Decimal:
        """Execute aggregate query on Oracle (e.g. SUM(amount), AVG(salary))."""
        adapted_sql = self._adapt_oracle_sql(projection_sql)
        if adapted_sql:
            sql = f"SELECT {metric_expr} FROM ({adapted_sql})"
        elif schema_name and table_name:
            sql = f'SELECT {metric_expr} FROM "{schema_name.upper()}"."{table_name.upper()}"'
        else:
            sql = f'SELECT {metric_expr} FROM "{table_name.upper()}"'

        val = self._execute_scalar(sql)
        if val is None:
            return Decimal(0)
        return Decimal(str(val))

    def fetch_null_count(self, column_name: str, projection_sql: str | None, table_name: str | None, schema_name: str | None) -> int:
        """Fetch null count for a column on Oracle."""
        adapted_sql = self._adapt_oracle_sql(projection_sql)
        if adapted_sql:
            sql = f'SELECT COUNT(*) FROM ({adapted_sql}) WHERE "{column_name}" IS NULL'
        elif schema_name and table_name:
            sql = f'SELECT COUNT(*) FROM "{schema_name.upper()}"."{table_name.upper()}" WHERE "{column_name}" IS NULL'
        else:
            sql = f'SELECT COUNT(*) FROM "{table_name.upper()}" WHERE "{column_name}" IS NULL'

        return self._execute_scalar_int(sql)

    def compute_data_digest(self, columns: list[str], projection_sql: str | None, table_name: str | None, schema_name: str | None) -> str:
        """Compute canonical SHA-256 digest of transformed source dataset."""
        if not columns:
            return hashlib.sha256(b"empty").hexdigest()

        # Canonical ordering and string formatting
        col_exprs = [f"COALESCE(TO_CHAR(\"{c}\"), 'NULL')" for c in columns]
        concat_expr = " || '|' || ".join(col_exprs)

        adapted_sql = self._adapt_oracle_sql(projection_sql)
        if adapted_sql:
            sql = f"SELECT {concat_expr} AS row_str FROM ({adapted_sql})"
        elif schema_name and table_name:
            sql = f'SELECT {concat_expr} AS row_str FROM "{schema_name.upper()}"."{table_name.upper()}"'
        else:
            sql = f'SELECT {concat_expr} AS row_str FROM "{table_name.upper()}"'

        rows = self._execute_all(sql)
        hasher = hashlib.sha256()
        for r in rows:
            row_text = str(r[0]) if r and r[0] is not None else "NULL"
            hasher.update(row_text.encode("utf-8"))
        return hasher.hexdigest()

    # ---- Internal Execution Helpers ----
    def _execute_scalar(self, sql: str) -> Any:
        try:
            import oracledb
            dsn = f"{self.host}:{self.port}/{self.service_name}"
            conn = oracledb.connect(user=self.user, password=self.password, dsn=dsn)
            with conn:
                cur = conn.cursor()
                cur.execute(sql)
                res = cur.fetchone()
                return res[0] if res else None
        except Exception as exc:
            raise RuntimeError(f"Oracle query error: {self.sanitize_error(exc)}")

    def _execute_scalar_int(self, sql: str) -> int:
        val = self._execute_scalar(sql)
        if val is None:
            return 0
        return int(val)

    def _execute_all(self, sql: str) -> list[tuple]:
        try:
            import oracledb
            dsn = f"{self.host}:{self.port}/{self.service_name}"
            conn = oracledb.connect(user=self.user, password=self.password, dsn=dsn)
            with conn:
                cur = conn.cursor()
                cur.execute(sql)
                return cur.fetchall()
        except Exception as exc:
            raise RuntimeError(f"Oracle query error: {self.sanitize_error(exc)}")


class PostgresService(BaseDbService):
    """PostgreSQL database access service."""

    def __init__(
        self,
        user: str = settings.POSTGRES_USER,
        password: str = settings.POSTGRES_PASSWORD,
        host: str = settings.POSTGRES_HOST,
        port: str = settings.POSTGRES_PORT,
        database: str = settings.POSTGRES_DATABASE,
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database

    def test_connection(self) -> tuple[bool, str]:
        """Test PostgreSQL database connectivity without exposing credentials."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                dbname=self.database,
                connect_timeout=5,
            )
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
            return True, f"Successfully connected to PostgreSQL at {self.host}:{self.port}/{self.database}"
        except Exception as exc:
            return False, f"PostgreSQL Connection Error: {self.sanitize_error(exc)}"

    def fetch_row_count(self, schema_name: str | None, table_name: str) -> int:
        """Fetch target table row count from PostgreSQL."""
        schema = schema_name or "public"
        sql = f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'
        return self._execute_scalar_int(sql)

    def fetch_aggregate(self, metric_expr: str, schema_name: str | None, table_name: str) -> Decimal:
        """Execute aggregate query on PostgreSQL."""
        schema = schema_name or "public"
        sql = f'SELECT {metric_expr} FROM "{schema}"."{table_name}"'
        val = self._execute_scalar(sql)
        if val is None:
            return Decimal(0)
        return Decimal(str(val))

    def fetch_null_count(self, column_name: str, schema_name: str | None, table_name: str) -> int:
        """Fetch NULL count for column on PostgreSQL."""
        schema = schema_name or "public"
        sql = f'SELECT COUNT(*) FROM "{schema}"."{table_name}" WHERE "{column_name}" IS NULL'
        return self._execute_scalar_int(sql)

    def compute_data_digest(self, columns: list[str], schema_name: str | None, table_name: str) -> str:
        """Compute canonical SHA-256 digest of PostgreSQL target dataset."""
        if not columns:
            return hashlib.sha256(b"empty").hexdigest()

        schema = schema_name or "public"
        col_exprs = [f"COALESCE(\"{c}\"::text, 'NULL')" for c in columns]
        concat_expr = " || '|' || ".join(col_exprs)

        sql = f'SELECT {concat_expr} AS row_str FROM "{schema}"."{table_name}"'

        rows = self._execute_all(sql)
        hasher = hashlib.sha256()
        for r in rows:
            row_text = str(r[0]) if r and r[0] is not None else "NULL"
            hasher.update(row_text.encode("utf-8"))
        return hasher.hexdigest()

    def inspect_schema_metadata(self, schema_name: str | None, table_name: str) -> dict[str, Any]:
        """
        Inspect actual PostgreSQL schema: columns, data types, nullability.
        Returns ``{"table_exists": bool, "columns": {"col_name": {"type": str, "nullable": bool}}}``.
        """
        schema = schema_name or "public"
        sql = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """
        rows = self._execute_params(sql, (schema.lower(), table_name.lower()))
        if not rows:
            return {"table_exists": False, "columns": {}}

        cols: dict[str, dict[str, Any]] = {}
        for r in rows:
            cols[r[0].lower()] = {
                "name": r[0],
                "type": r[1],
                "nullable": r[2].upper() == "YES",
            }
        return {"table_exists": True, "columns": cols}

    # ---- Internal Execution Helpers ----
    def _execute_scalar(self, sql: str) -> Any:
        try:
            import psycopg2
            conn = psycopg2.connect(
                user=self.user, password=self.password, host=self.host, port=self.port, dbname=self.database
            )
            with conn:
                cur = conn.cursor()
                cur.execute(sql)
                res = cur.fetchone()
                return res[0] if res else None
        except Exception as exc:
            raise RuntimeError(f"PostgreSQL query error: {self.sanitize_error(exc)}")

    def _execute_scalar_int(self, sql: str) -> int:
        val = self._execute_scalar(sql)
        if val is None:
            return 0
        return int(val)

    def _execute_all(self, sql: str) -> list[tuple]:
        try:
            import psycopg2
            conn = psycopg2.connect(
                user=self.user, password=self.password, host=self.host, port=self.port, dbname=self.database
            )
            with conn:
                cur = conn.cursor()
                cur.execute(sql)
                return cur.fetchall()
        except Exception as exc:
            raise RuntimeError(f"PostgreSQL query error: {self.sanitize_error(exc)}")

    def _execute_params(self, sql: str, params: tuple) -> list[tuple]:
        try:
            import psycopg2
            conn = psycopg2.connect(
                user=self.user, password=self.password, host=self.host, port=self.port, dbname=self.database
            )
            with conn:
                cur = conn.cursor()
                cur.execute(sql, params)
                return cur.fetchall()
        except Exception as exc:
            raise RuntimeError(f"PostgreSQL query error: {self.sanitize_error(exc)}")
