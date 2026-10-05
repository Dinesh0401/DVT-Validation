#!/usr/bin/env python3
"""
common.py — Shared Universal Utilities for Migration Preflight & DVT Generation.

Provides dialect-agnostic, zero-hardcoding helpers for:
  - Database engine inference (from JDBC URL, driver class, or metadata)
  - DVT CLI engine type mapping (Postgres, Oracle, MySQL, SqlServer, etc.)
  - Universal SQL relation parsing (catalog/schema/table in any quoting style)
  - Dynamic input file discovery (CLI args, env vars, or auto-discovery)
  - Default connection ports for major database engines
"""

import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
INPUT = BASE / "input"
GENERATED = BASE / "generated"
REPORTS = BASE / "reports"
SCRIPTS = BASE / "scripts"
DVT_CONFIGS_DIR = GENERATED / "dvt_configs"

# Default network ports for standard database engines
DEFAULT_PORTS = {
    "oracle": 1521,
    "postgresql": 5432,
    "postgres": 5432,
    "mysql": 3306,
    "mariadb": 3306,
    "sqlserver": 1433,
    "mssql": 1433,
    "db2": 50000,
    "hive": 10000,
    "snowflake": 443,
    "bigquery": 443,
    "clickhouse": 8123,
    "redshift": 5439,
    "sqlite": 0,
}


def infer_engine(driver_str: str = "", url_str: str = "", comment_str: str = "") -> str:
    """
    Dynamically infers the database engine without static table or engine lock-in.
    Inspects comments, JDBC URL schemes, or JDBC driver class package names.
    """
    if comment_str and comment_str.strip():
        val = comment_str.strip().title()
        return "PostgreSQL" if val.lower() in ("postgres", "postgresql") else val

    if url_str:
        m = re.search(r'jdbc:([a-zA-Z0-9_\-]+):', url_str, re.IGNORECASE)
        if m:
            eng = m.group(1).lower()
            return "PostgreSQL" if eng in ("postgres", "postgresql") else eng.title()

    if driver_str:
        d_lower = driver_str.lower()
        known = (
            "oracle", "postgresql", "postgres", "mysql", "mariadb",
            "sqlserver", "snowflake", "bigquery", "sqlite", "db2",
            "hive", "clickhouse", "redshift", "trino", "presto"
        )
        for token in known:
            if token in d_lower:
                return "PostgreSQL" if token in ("postgres", "postgresql") else token.title()
        parts = driver_str.split('.')
        if len(parts) >= 2:
            return parts[-2].title()

    return "GenericSQL"


def dvt_engine_type(engine_name: str) -> str:
    """
    Maps any database engine name to Google Cloud Data Validation Tool (DVT) connection type.
    DVT CLI recognizes: Oracle, Postgres, MySQL, SqlServer, Snowflake, BigQuery, Redshift, DB2, Hive, etc.
    """
    eng = (engine_name or "").strip().lower()
    mapping = {
        "postgresql": "Postgres",
        "postgres": "Postgres",
        "oracle": "Oracle",
        "mysql": "MySQL",
        "mariadb": "MySQL",
        "sqlserver": "SqlServer",
        "mssql": "SqlServer",
        "snowflake": "Snowflake",
        "bigquery": "BigQuery",
        "redshift": "Redshift",
        "db2": "DB2",
        "hive": "Hive",
        "sqlite": "SQLite",
    }
    return mapping.get(eng, engine_name.title() if engine_name else "GenericSQL")


def parse_relation_identifier(rel_str: str) -> tuple:
    """
    Universally parses any relation identifier into (schema, table).
    Handles 'catalog.schema.table', '"schema"."table"', '[schema].[table]', '`schema`.`table`', bare 'table'.
    """
    if not rel_str:
        return ("", "")
    cleaned = (
        rel_str.replace('\\', '')
        .replace('"', '')
        .replace("'", "")
        .replace('[', '')
        .replace(']', '')
        .replace('`', '')
        .strip()
    )
    parts = [p.strip() for p in cleaned.split('.') if p.strip()]
    if len(parts) >= 2:
        return (parts[-2], parts[-1])
    elif len(parts) == 1:
        return ("", parts[0])
    return ("", cleaned)


def normalize_relation(rel_str: str) -> str:
    """Normalizes any relation to 'schema.table' or 'table' in lowercase for comparison."""
    if not rel_str:
        return ""
    schema, table = parse_relation_identifier(rel_str)
    return f"{schema.lower()}.{table.lower()}" if schema else table.lower()


def resolve_input_paths(contract_arg: str = None, plan_arg: str = None) -> tuple:
    """
    Dynamically discovers input contract and plan paths.
    Prioritizes:
      1. Explicit CLI arguments (--contract, --plan)
      2. Environment variables (MIGRATION_CONTRACT_PATH, MIGRATION_PLAN_PATH)
      3. Auto-discovery in the input/ folder (any .yaml/.yml and any .conf/.txt)
    """
    contract_path = Path(contract_arg) if contract_arg else None
    plan_path = Path(plan_arg) if plan_arg else None

    if not contract_path and os.environ.get("MIGRATION_CONTRACT_PATH"):
        contract_path = Path(os.environ["MIGRATION_CONTRACT_PATH"])
    if not plan_path and os.environ.get("MIGRATION_PLAN_PATH"):
        plan_path = Path(os.environ["MIGRATION_PLAN_PATH"])

    if not contract_path or not contract_path.exists():
        yaml_candidates = sorted(list(INPUT.glob("*.yaml")) + list(INPUT.glob("*.yml")))
        if yaml_candidates:
            contract_path = yaml_candidates[0]

    if not plan_path or not plan_path.exists():
        conf_candidates = sorted(list(INPUT.glob("*.conf*")) + list(INPUT.glob("*.txt")))
        if conf_candidates:
            plan_path = conf_candidates[0]

    return contract_path, plan_path
