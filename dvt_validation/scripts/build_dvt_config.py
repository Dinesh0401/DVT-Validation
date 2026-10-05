#!/usr/bin/env python3
"""
build_dvt_config.py — Generic Stage-1 DVT Plan & Artifact Builder.

Generates validated DVT plans, executable CLI commands, and native DVT YAML
configs dynamically for any source engine and target engine without hardcoding.

Outputs (generated/):
  dvt_validation_plan.yaml   comprehensive Stage-1 validation specification
  dvt_cli_commands.sh        executable bash commands for Google Cloud DVT CLI
  dvt_cli_commands.bat       executable windows batch commands for DVT CLI
  dvt_configs/*.yaml         native DVT configurations for `data-validation configs run`
"""

import json
import re
import sys
from pathlib import Path
import yaml

# Ensure scripts dir is in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import (
    BASE, GENERATED, DVT_CONFIGS_DIR,
    DEFAULT_PORTS,
    parse_relation_identifier,
    dvt_engine_type,
)


def build_validation_plan(manifest: dict) -> dict:
    meta = manifest.get("metadata", {})
    src_engine = meta.get("detected_source_engine", "SourceDB")
    tgt_engine = meta.get("detected_target_engine", "TargetDB")

    src_dvt_type = dvt_engine_type(src_engine)
    tgt_dvt_type = dvt_engine_type(tgt_engine)

    src_conn_name = f"{src_engine.lower()}_source"
    tgt_conn_name = f"{tgt_engine.lower()}_target"

    src_default_port = DEFAULT_PORTS.get(src_engine.lower(), 1521)
    tgt_default_port = DEFAULT_PORTS.get(tgt_engine.lower(), 5432)

    declared_bindings = meta.get("bindings", {})
    binding_str = ", ".join(f"${{{k}}}" for k in declared_bindings.keys()) if declared_bindings else "${run_scn}"

    plan = {
        "metadata": {
            "title": f"Stage-1 Pre-migration DVT Validation Plan ({src_engine} -> {tgt_engine})",
            "source_engine": src_engine,
            "target_engine": tgt_engine,
            "generated_by": "Stage-1 Generic Preflight Pipeline",
            "convention": {
                "zero_rows_means_pass": True,
                "nonzero_rows_means_fail": True,
                "acquisition": meta.get("acquisition", "snapshot"),
                "snapshot_binding": binding_str,
            },
        },
        "connections": {
            "source": {
                "name": src_conn_name,
                "type": src_dvt_type,
                "host": "${" + src_engine.upper() + "_HOST}",
                "port": "${" + src_engine.upper() + f"_PORT:-{src_default_port}" + "}",
                "database": "${" + src_engine.upper() + "_DATABASE}",
                "user": "${" + src_engine.upper() + "_DB_USER}",
                "password": "${" + src_engine.upper() + "_DB_PASSWORD}",
            },
            "target": {
                "name": tgt_conn_name,
                "type": tgt_dvt_type,
                "host": "${" + tgt_engine.upper() + "_HOST}",
                "port": "${" + tgt_engine.upper() + f"_PORT:-{tgt_default_port}" + "}",
                "database": "${" + tgt_engine.upper() + "_DATABASE}",
                "user": "${" + tgt_engine.upper() + "_DB_USER}",
                "password": "${" + tgt_engine.upper() + "_DB_PASSWORD}",
            },
        },
        "jobs": [],
    }

    for entry in manifest["jobs"]:
        jid = entry["job_id"]
        status = entry["status"]
        if status == "BLOCKED":
            plan["jobs"].append({
                "job_id": jid,
                "status": "BLOCKED",
                "reason": entry.get("reason"),
            })
            continue

        d = entry.get("duckdb") or {}
        s = entry.get("seatunnel") or {}

        # Resolve Source and Target relations dynamically
        raw_rels = d.get("raw_relations", [])
        src_raw = raw_rels[0].get("relation", "") if raw_rels else s.get("source", "")
        src_schema, src_table = parse_relation_identifier(src_raw)

        tgt_rel = d.get("target_relation") or s.get("target", "")
        tgt_schema, tgt_table = parse_relation_identifier(tgt_rel)

        pk = s.get("primary_key")
        primary_keys = [pk] if pk else []

        # Dynamically determine if query involves transformations
        source_proj = d.get("source_projection", "").upper()
        is_complex = any(kw in source_proj for kw in ("JOIN", "UNION", "GROUP BY", "ROW_NUMBER()", "OVER (", "DISTINCT"))

        # Categorize contract checks dynamically
        checks = d.get("checks", [])
        sql_checks = [c for c in checks if c.get("sql")]
        runtime_checks = [c for c in checks if not c.get("sql")]

        job_plan = {
            "job_id": jid,
            "order": d.get("order"),
            "status": "READY",
            "source": {
                "connection": src_conn_name,
                "schema": src_schema,
                "table": src_table,
                "snapshot_binding": binding_str,
                "query": s.get("source_query"),
            },
            "target": {
                "connection": tgt_conn_name,
                "schema": tgt_schema,
                "table": tgt_table,
            },
            "primary_keys": primary_keys,
            "validation_strategy": {
                "is_complex_transformation": is_complex,
                "native_dvt_schema": True,
                "native_dvt_row": not is_complex,
                "dvt_custom_query": is_complex,
            },
            "contract_coverage": {
                "total_checks": len(checks),
                "checks_with_sql": len(sql_checks),
                "runtime_only_checks": len(runtime_checks),
                "sql_checks_summary": [c["check_id"] for c in sql_checks],
            },
        }
        plan["jobs"].append(job_plan)

    return plan


def generate_dvt_cli_scripts(plan: dict):
    """Generate shell script and Windows bat script containing DVT CLI commands dynamically."""
    src_conn = plan["connections"]["source"]["name"]
    tgt_conn = plan["connections"]["target"]["name"]

    sh_lines = [
        "#!/usr/bin/env bash",
        "# Google Cloud Data Validation Tool (DVT) Execution Script",
        "# Generated dynamically by Stage-1 Preflight Pipeline",
        "# Use --dry-run to print generated SQL without executing data validation",
        "",
        "DRY_RUN_FLAG=\"${1:---dry-run}\"",
        f"SRC_CONN=\"{src_conn}\"",
        f"TGT_CONN=\"{tgt_conn}\"",
        "",
        "echo \"===================================================\"",
        f"echo \"Running DVT Validations ({src_conn} -> {tgt_conn}) with mode: $DRY_RUN_FLAG\"",
        "echo \"===================================================\"",
        "",
    ]

    bat_lines = [
        "@echo off",
        "rem Google Cloud Data Validation Tool (DVT) Execution Script",
        "rem Generated dynamically by Stage-1 Preflight Pipeline",
        "set DRY_RUN_FLAG=%1",
        "if \"%DRY_RUN_FLAG%\"==\"\" set DRY_RUN_FLAG=--dry-run",
        f"set SRC_CONN={src_conn}",
        f"set TGT_CONN={tgt_conn}",
        "",
        "echo ===================================================",
        f"echo Running DVT Validations ({src_conn} -> {tgt_conn}) with mode: %DRY_RUN_FLAG%",
        "echo ===================================================",
        "",
    ]

    for job in plan["jobs"]:
        if job.get("status") == "BLOCKED":
            continue

        jid = job["job_id"]
        src = job["source"]
        tgt = job["target"]
        strat = job["validation_strategy"]
        pk = job.get("primary_keys")

        src_full = f"{src['schema']}.{src['table']}" if src['schema'] else src['table']
        tgt_full = f"{tgt['schema']}.{tgt['table']}" if tgt['schema'] else tgt['table']
        tbl_map = f"{src_full}={tgt_full}"
        pk_flag = f"--primary-keys {pk[0]}" if pk else ""

        # Schema Validation
        cmd_schema = f"data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls {tbl_map} $DRY_RUN_FLAG"
        cmd_schema_bat = f"data-validation validate schema -sc %SRC_CONN% -tc %TGT_CONN% -tbls {tbl_map} %DRY_RUN_FLAG%"

        sh_lines.append(f"# --- {jid} ---")
        sh_lines.append(f"echo \"[DVT] Validating Schema: {jid} ({tbl_map})\"")
        sh_lines.append(cmd_schema)

        bat_lines.append(f"rem --- {jid} ---")
        bat_lines.append(f"echo [DVT] Validating Schema: {jid} ({tbl_map})")
        bat_lines.append(cmd_schema_bat)

        # Row or Custom Query Validation
        if strat["native_dvt_row"]:
            cmd_row = f"data-validation validate row -sc $SRC_CONN -tc $TGT_CONN -tbls {tbl_map} {pk_flag} $DRY_RUN_FLAG".strip()
            cmd_row_bat = f"data-validation validate row -sc %SRC_CONN% -tc %TGT_CONN% -tbls {tbl_map} {pk_flag} %DRY_RUN_FLAG%".strip()
            sh_lines.append(f"echo \"[DVT] Validating Row Counts: {jid}\"")
            sh_lines.append(cmd_row)
            bat_lines.append(f"echo [DVT] Validating Row Counts: {jid}")
            bat_lines.append(cmd_row_bat)
        else:
            sh_lines.append(f"echo \"[DVT] Complex Transform: Custom Query Validation recommended for {jid}\"")
            bat_lines.append(f"echo [DVT] Complex Transform: Custom Query Validation recommended for {jid}")

        sh_lines.append("")
        bat_lines.append("")

    (GENERATED / "dvt_cli_commands.sh").write_text("\n".join(sh_lines), encoding="utf-8")
    (GENERATED / "dvt_cli_commands.bat").write_text("\n".join(bat_lines), encoding="utf-8")


def generate_native_dvt_configs(plan: dict):
    """Generate official DVT-compliant YAML configs for `data-validation configs run` dynamically."""
    DVT_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    src_conn = plan["connections"]["source"]["name"]
    tgt_conn = plan["connections"]["target"]["name"]

    for job in plan["jobs"]:
        if job.get("status") == "BLOCKED":
            continue

        jid = job["job_id"]
        src = job["source"]
        tgt = job["target"]
        pk = job.get("primary_keys")

        schema_cfg = {
            "schema_validation": {
                "source_conn_name": src_conn,
                "target_conn_name": tgt_conn,
                "schema_name": src["schema"],
                "table_name": src["table"],
                "target_schema_name": tgt["schema"],
                "target_table_name": tgt["table"],
            }
        }
        with open(DVT_CONFIGS_DIR / f"schema_{jid}.yaml", "w", encoding="utf-8") as f:
            yaml.dump(schema_cfg, f, sort_keys=False, indent=2)

        data_cfg = {
            "data_validation": {
                "source_conn_name": src_conn,
                "target_conn_name": tgt_conn,
                "schema_name": src["schema"],
                "table_name": src["table"],
                "target_schema_name": tgt["schema"],
                "target_table_name": tgt["table"],
                "primary_keys": [{"source_column": pk[0], "target_column": pk[0]}] if pk else [],
                "validation_type": "Row",
            }
        }
        with open(DVT_CONFIGS_DIR / f"row_{jid}.yaml", "w", encoding="utf-8") as f:
            yaml.dump(data_cfg, f, sort_keys=False, indent=2)


def main():
    manifest_path = GENERATED / "jobs.json"
    if not manifest_path.exists():
        print(f"FATAL: {manifest_path} not found. Please run extract_jobs.py first.", file=sys.stderr)
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    plan = build_validation_plan(manifest)

    # Write plan YAML
    plan_yaml_path = GENERATED / "dvt_validation_plan.yaml"
    with open(plan_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(plan, f, sort_keys=False, indent=2)

    # Generate CLI scripts and configs dynamically
    generate_dvt_cli_scripts(plan)
    generate_native_dvt_configs(plan)

    n_active = sum(1 for j in plan["jobs"] if j.get("status") == "READY")
    src_eng = plan["metadata"]["source_engine"]
    tgt_eng = plan["metadata"]["target_engine"]

    print(f"Generated Dynamic Stage-1 DVT Artifacts for {n_active} active jobs ({src_eng} -> {tgt_eng}):")
    print(f"  - Validation Plan : {plan_yaml_path}")
    print(f"  - CLI Bash Script : {GENERATED / 'dvt_cli_commands.sh'}")
    print(f"  - CLI Batch Script: {GENERATED / 'dvt_cli_commands.bat'}")
    print(f"  - Native Configs  : {DVT_CONFIGS_DIR} ({n_active * 2} YAML files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
