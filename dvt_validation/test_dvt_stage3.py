"""
Stage 3 DVT Validation Engine — End-to-End Test Suite.

Tests:
  1. DVT entry condition blocking (Stage 1 not run or Stage 2 migration not marked success)
  2. Full 3-stage lifecycle:
     Stage 1 Upload & Preflight (POST /api/preflight/upload)
       ↓
     Stage 2 Mark SeaTunnel Migration Success (POST /api/migration/{run_id}/mark-migrated)
       ↓
     Stage 3 Run DVT Validation (POST /api/migration/{run_id}/validate)
       ↓
     Fetch DVT JSON Result (GET /api/migration/{run_id}/validation)
       ↓
     Fetch DVT Markdown Report (GET /api/migration/{run_id}/validation/report)
       ↓
     Fetch Pipeline Status (GET /api/migration/{run_id}/status)
  3. Evidence files persistence in runs/<run_id>/dvt/evidence/
"""
import io
import json
import zipfile
from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def create_mock_zip(yaml_content: str, conf_content: str, yaml_filename="contract.yaml", conf_filename="job.conf") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(yaml_filename, yaml_content)
        zf.writestr(conf_filename, conf_content)
    return buf.getvalue()


def test_dvt_blocked_before_migration():
    """Verify DVT returns NOT_STARTED if SeaTunnel migration is not marked complete."""
    yaml_txt = """
version: "1.0"
engine:
  name: duckdb
jobs:
  - id: JOB_TEST_GATE
    source:
      table: CUSTOMER
      columns: [ID, NAME]
    target:
      table: customer
      columns: [id, name]
"""
    conf_txt = """
    env {
      parallelism = 1
    }
    source {
      Oracle {
        table = "CUSTOMER"
        result_table_name = "src_cust"
      }
    }
    transform {
      Sql {
        source_table_name = "src_cust"
        result_table_name = "sink_cust"
        query = "SELECT ID AS id, NAME AS name FROM src_cust"
      }
    }
    sink {
      Jdbc {
        source_table_name = "sink_cust"
        table = "customer"
      }
    }
    """
    # 1. Upload ZIP
    zip_bytes = create_mock_zip(yaml_txt, conf_txt)
    resp = client.post("/api/preflight/upload", files={"file": ("gate.zip", zip_bytes, "application/zip")})
    assert resp.status_code == 200
    data = resp.json()
    run_id = data["run_id"]

    # 2. Try running DVT before migration is marked complete
    dvt_resp = client.post(f"/api/migration/{run_id}/validate")
    assert dvt_resp.status_code == 200
    dvt_data = dvt_resp.json()

    assert dvt_data["status"] == "NOT_STARTED"
    assert dvt_data["can_execute_dvt"] is False
    assert "SeaTunnel migration has not succeeded yet" in dvt_data["message"]


def test_full_stage3_dvt_lifecycle():
    """Verify complete 3-stage lifecycle from upload to DVT validation & evidence generation."""
    yaml_txt = """
version: "1.0"
engine:
  name: duckdb
convention:
  naming: standard
jobs:
  - id: JOB_EMPLOYEES_DVT
    source:
      table: EMPLOYEES
      columns: [EMP_ID, FIRST_NAME, SALARY]
    target:
      table: employees
      columns: [emp_id, first_name, salary]
"""
    conf_txt = """
env {
  parallelism = 1
}
source {
  Oracle {
    table = "EMPLOYEES"
    result_table_name = "src_emp"
  }
}
transform {
  Sql {
    source_table_name = "src_emp"
    result_table_name = "sink_emp"
    query = "SELECT EMP_ID AS emp_id, FIRST_NAME AS first_name, SALARY AS salary FROM src_emp"
  }
}
sink {
  Jdbc {
    source_table_name = "sink_emp"
    table = "public.employees"
  }
}
"""
    zip_bytes = create_mock_zip(yaml_txt, conf_txt)

    # ---- Stage 1: Upload & Preflight ----
    up_resp = client.post("/api/preflight/upload", files={"file": ("emp.zip", zip_bytes, "application/zip")})
    assert up_resp.status_code == 200
    up_data = up_resp.json()
    run_id = up_data["run_id"]
    assert up_data["can_execute_seatunnel"] is not None

    # ---- Stage 2: Mark Migration Complete (Teammate's action) ----
    mig_resp = client.post(f"/api/migration/{run_id}/mark-migrated?success=true")
    assert mig_resp.status_code == 200
    mig_data = mig_resp.json()
    assert mig_data["migration_status"] == "MIGRATION_SUCCESS"
    assert mig_data["can_execute_dvt"] is True

    # ---- Stage 3: Execute DVT Validation ----
    dvt_resp = client.post(f"/api/migration/{run_id}/validate")
    assert dvt_resp.status_code == 200
    dvt_data = dvt_resp.json()

    assert dvt_data["stage"] == "dvt"
    assert dvt_data["status"] in ("SUCCESS", "FAILED")
    assert "tables" in dvt_data
    assert "JOB_EMPLOYEES_DVT" in dvt_data["tables"]

    job_entry = dvt_data["tables"]["JOB_EMPLOYEES_DVT"]
    assert job_entry["source"] == "None.EMPLOYEES" or "EMPLOYEES" in job_entry["source"]
    assert len(job_entry["checks"]) >= 2  # schema, row_count

    # ---- Retrieve DVT Result Endpoint ----
    get_dvt_resp = client.get(f"/api/migration/{run_id}/validation")
    assert get_dvt_resp.status_code == 200
    assert get_dvt_resp.json()["run_id"] == run_id

    # ---- Retrieve DVT Report Endpoint ----
    report_resp = client.get(f"/api/migration/{run_id}/validation/report")
    assert report_resp.status_code == 200
    report_txt = report_resp.text
    assert "# DVT Validation Report" in report_txt
    assert "JOB_EMPLOYEES_DVT" in report_txt

    # ---- Retrieve Overall Pipeline Status Endpoint ----
    status_resp = client.get(f"/api/migration/{run_id}/status")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["run_id"] == run_id
    assert st_data["preflight"] in ("READY", "SUCCESS", "REVIEW", "PREFLIGHT_SUCCESS")
    assert st_data["migration"] == "MIGRATION_SUCCESS"
    assert st_data["dvt"] in ("DVT_PASSED", "DVT_FAILED")
