"""
Unit & Integration tests for the Generic Preflight Validation Engine.

Tests:
  1. Valid ZIP extraction & file discovery
  2. YAML parsing & structure validation
  3. SeaTunnel HOCON parsing & job extraction
  4. Cross-validation failure cases:
     - Table mismatch (YAML source vs SeaTunnel source table)
     - Target table mismatch
     - Missing column in SeaTunnel
     - SCN / Snapshot binding mismatch
"""
import io
import zipfile
from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def create_mock_zip(yaml_content: str, conf_content: str, yaml_filename="contract.yaml", conf_filename="job.conf") -> bytes:
    """Utility to generate an in-memory ZIP package."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(yaml_filename, yaml_content)
        zf.writestr(conf_filename, conf_content)
    return buf.getvalue()


def test_clean_pass_dynamic():
    yaml_txt = """
version: "1.0"
source:
  database_type: Oracle
  schema: HR_APP
target:
  database_type: PostgreSQL
  schema: hr_public
jobs:
  - id: JOB_001
    source:
      table: DEPARTMENTS
      columns: [DEPT_ID, DEPT_NAME, MANAGER_ID]
    target:
      table: departments
      columns: [dept_id, dept_name, manager_id]
"""
    conf_txt = """
env {
  parallelism = 1
}
source {
  Oracle-CDC {
    schema-name = "HR_APP"
    table-name = "DEPARTMENTS"
    result_table_name = "src_dept"
  }
}
transform {
  Sql {
    source_table_name = "src_dept"
    result_table_name = "sink_dept"
    query = "SELECT DEPT_ID AS dept_id, DEPT_NAME AS dept_name, MANAGER_ID AS manager_id FROM src_dept"
  }
}
sink {
  Jdbc {
    source_table_name = "sink_dept"
    table = "hr_public.departments"
  }
}
"""
    zip_bytes = create_mock_zip(yaml_txt, conf_txt)
    resp = client.post("/api/preflight/upload", files={"file": ("mock.zip", zip_bytes, "application/zip")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["summary"]["failed"] == 0


def test_missing_column_mismatch():
    yaml_txt = """
version: "1.0"
jobs:
  - id: JOB_PAYROLL
    source:
      table: SALARIES
      columns: [EMP_ID, SALARY, BONUS, TAX_DEDUCTION]
    target:
      table: salaries
      columns: [emp_id, salary, bonus, tax_deduction]
"""
    conf_txt = """
source {
  Oracle {
    table = "SALARIES"
    result_table_name = "src_sal"
  }
}
transform {
  Sql {
    source_table_name = "src_sal"
    result_table_name = "sink_sal"
    query = "SELECT EMP_ID, SALARY, BONUS FROM src_sal"
  }
}
sink {
  Jdbc {
    source_table_name = "sink_sal"
    table = "salaries"
  }
}
"""
    zip_bytes = create_mock_zip(yaml_txt, conf_txt)
    resp = client.post("/api/preflight/upload", files={"file": ("payroll.zip", zip_bytes, "application/zip")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    problems = data["problems"]
    missing_cols = [p for p in problems if p["type"] in ("MISSING_COLUMN", "COLUMN_MISMATCH")]
    assert len(missing_cols) > 0
    assert any("TAX_DEDUCTION" in p["message"] or "tax_deduction" in p["message"] for p in missing_cols)


def test_target_table_mismatch():
    yaml_txt = """
jobs:
  - id: JOB_INV
    source:
      table: INVENTORY
      columns: [SKU, QTY]
    target:
      table: tbl_inventory_v2
      columns: [sku, qty]
"""
    conf_txt = """
source {
  Jdbc {
    table = "INVENTORY"
    result_table_name = "src_inv"
  }
}
sink {
  Jdbc {
    source_table_name = "src_inv"
    table = "wrong_table_name"
  }
}
"""
    zip_bytes = create_mock_zip(yaml_txt, conf_txt)
    resp = client.post("/api/preflight/upload", files={"file": ("inv.zip", zip_bytes, "application/zip")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    target_errs = [p for p in data["problems"] if p["type"] == "TARGET_TABLE_MISMATCH"]
    assert len(target_errs) == 1
    assert target_errs[0]["expected"] == "tbl_inventory_v2"
    assert target_errs[0]["actual"] == "wrong_table_name"


def test_scn_snapshot_requirement():
    yaml_txt = """
jobs:
  - id: JOB_SCN
    scn_snapshot:
      required: true
      start_scn: 12345678
    source:
      table: TRANSACTIONS
      columns: [TX_ID, AMOUNT]
    target:
      table: transactions
      columns: [tx_id, amount]
"""
    # SeaTunnel source missing SCN binding
    conf_txt = """
source {
  Oracle {
    table = "TRANSACTIONS"
    result_table_name = "src_tx"
  }
}
sink {
  Jdbc {
    source_table_name = "src_tx"
    table = "transactions"
  }
}
"""
    zip_bytes = create_mock_zip(yaml_txt, conf_txt)
    resp = client.post("/api/preflight/upload", files={"file": ("scn.zip", zip_bytes, "application/zip")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    scn_errs = [p for p in data["problems"] if p["type"] == "SCN_BINDING_MISSING"]
    assert len(scn_errs) == 1
    assert "start_scn" in scn_errs[0]["message"] or "12345678" in scn_errs[0]["message"]
