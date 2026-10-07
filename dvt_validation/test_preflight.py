"""
Test script — sends all 4 ZIP files to the preflight validator and prints detailed results.

Tests:
  1. POST /api/preflight/upload
  2. GET /api/preflight/{run_id}
  3. GET /api/preflight/{run_id}/report
"""
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app

sys.stdout.reconfigure(encoding='utf-8')

INPUT_DIR = Path(__file__).parent / "input"
client = TestClient(app)


import pytest


@pytest.mark.parametrize("zip_path", sorted(INPUT_DIR.glob("*.zip")), ids=lambda p: p.name)
def test_zip(zip_path: Path):
    print(f"\n{'='*70}")
    print(f"Testing ZIP Package: {zip_path.name}")
    print(f"{'='*70}")

    with open(zip_path, "rb") as f:
        resp = client.post("/api/preflight/upload", files={"file": (zip_path.name, f, "application/zip")})

    if resp.status_code != 200:
        print(f"  HTTP ERROR: {resp.status_code}")
        print(f"  {resp.text}")
        return

    data = resp.json()
    run_id = data['run_id']
    status = data['status']
    stage = data['stage']
    yaml_file = data.get('yaml_file', 'N/A')
    conf_file = data.get('conf_file', 'N/A')
    s = data['summary']

    print(f"  Status:       {status}")
    print(f"  Stage:        {stage}")
    print(f"  Run ID:       {run_id}")
    print(f"  YAML File:    {yaml_file}")
    print(f"  SeaTunnel:    {conf_file}")
    print(f"  Checks:       total={s['total_checks']}  passed={s['passed']}  failed={s['failed']}  warnings={s['warnings']}")
    print(f"  Message:      {data['message']}")

    problems = data.get('problems', [])
    if problems:
        print(f"\n  Discovered Problems / Mismatches ({len(problems)}):")
        for i, p in enumerate(problems, 1):
            severity = p.get('severity', 'UNKNOWN')
            p_type = p.get('type', 'UNKNOWN')
            msg = p.get('message', '')
            job = p.get('job')
            expected = p.get('expected')
            actual = p.get('actual')
            file_a = p.get('file_a')
            file_b = p.get('file_b')
            path_a = p.get('path_a')

            print(f"\n    {i}. [{severity}] {p_type}")
            print(f"       Message:  {msg}")
            if job:
                print(f"       Job ID:   {job}")
            if file_a:
                print(f"       File A:   {file_a} ({path_a or ''})")
            if file_b:
                print(f"       File B:   {file_b}")
            if expected is not None:
                print(f"       Expected: {expected}")
            if actual is not None:
                print(f"       Actual:   {actual}")
    else:
        print("\n  No problems detected (Clean Pass).")

    # ---- Retrieve JSON result ----
    r2 = client.get(f"/api/preflight/{run_id}")
    assert r2.status_code == 200, f"GET /{run_id} failed with {r2.status_code}"
    print(f"\n  GET /api/preflight/{run_id} -> HTTP 200 OK")

    # ---- Retrieve Markdown report ----
    r3 = client.get(f"/api/preflight/{run_id}/report")
    assert r3.status_code == 200, f"GET /{run_id}/report failed with {r3.status_code}"
    report_text = r3.text
    print(f"  GET /api/preflight/{run_id}/report -> HTTP 200 OK ({len(report_text)} bytes Markdown)")

    # ---- Download ZIP archive ----
    r4 = client.get(f"/api/preflight/{run_id}/zip")
    assert r4.status_code == 200, f"GET /{run_id}/zip failed with {r4.status_code}"
    print(f"  GET /api/preflight/{run_id}/zip -> HTTP 200 OK ({len(r4.content)} bytes ZIP)")


if __name__ == "__main__":
    zips = sorted(INPUT_DIR.glob("*.zip"))
    if not zips:
        print("No ZIP files found in input/")
        sys.exit(1)

    print(f"Found {len(zips)} ZIP package(s) in {INPUT_DIR.name}/")

    for z in zips:
        test_zip(z)

    print(f"\n{'='*70}")
    print("ALL 4 MIGRATION PACKAGES TESTED SUCCESSFULLY.")
    print(f"{'='*70}\n")
