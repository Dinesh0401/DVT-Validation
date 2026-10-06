"""
Test script — sends all 4 ZIP files to the preflight validator and prints results.
"""
import json
import sys
from pathlib import Path

import requests

API_URL = "http://localhost:8000/api/preflight/upload"
INPUT_DIR = Path(__file__).parent / "input"

def test_zip(zip_path: Path):
    print(f"\n{'='*60}")
    print(f"Testing: {zip_path.name}")
    print(f"{'='*60}")

    with open(zip_path, "rb") as f:
        resp = requests.post(API_URL, files={"file": (zip_path.name, f, "application/zip")})

    if resp.status_code != 200:
        print(f"  HTTP ERROR: {resp.status_code}")
        print(f"  {resp.text}")
        return

    data = resp.json()
    print(f"  Status:   {data['status']}")
    print(f"  Stage:    {data['stage']}")
    print(f"  Run ID:   {data['run_id']}")
    print(f"  YAML:     {data.get('yaml_file', 'N/A')}")
    print(f"  .conf:    {data.get('conf_file', 'N/A')}")
    s = data['summary']
    print(f"  Summary:  total={s['total_checks']}  passed={s['passed']}  failed={s['failed']}  warnings={s['warnings']}")
    print(f"  Message:  {data['message']}")

    if data['problems']:
        print(f"\n  Problems ({len(data['problems'])}):")
        for i, p in enumerate(data['problems'], 1):
            print(f"    {i}. [{p['severity']}] {p['type']}")
            print(f"       {p['message']}")
            if p.get('job'):
                print(f"       Job: {p['job']}")
            if p.get('expected') is not None:
                print(f"       Expected: {p['expected']}")
            if p.get('actual') is not None:
                print(f"       Actual:   {p['actual']}")
    else:
        print("\n  No problems detected.")

    # Also test the retrieval endpoints
    run_id = data['run_id']
    r2 = requests.get(f"http://localhost:8000/api/preflight/{run_id}")
    print(f"\n  GET /{run_id}: {r2.status_code}")

    r3 = requests.get(f"http://localhost:8000/api/preflight/{run_id}/report")
    print(f"  GET /{run_id}/report: {r3.status_code} ({len(r3.text)} bytes)")


if __name__ == "__main__":
    zips = sorted(INPUT_DIR.glob("*.zip"))
    if not zips:
        print("No ZIP files found in input/")
        sys.exit(1)

    print(f"Found {len(zips)} ZIP file(s) in {INPUT_DIR}")

    for z in zips:
        test_zip(z)

    print(f"\n{'='*60}")
    print("All tests complete.")
