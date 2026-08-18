import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests


BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8001")
API_URL = f"{BACKEND_URL.rstrip('/')}/api"
EMAIL = os.environ.get("TEST_EMAIL", "admin@mssp-soc.io")
PASSWORD = os.environ.get("TEST_PASSWORD", "Admin@2026!")
OUT_DIR = Path("/app/test_reports/upload_artifacts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TI_COLUMNS = ["Advisories Name ", "Industry", "Date of Release", "IPs ", "Domain", "Hash", "Hash Type"]


def write_files():
    full = pd.DataFrame(
        [
            ["CVE-2026-0001 advisory", "Finance", "2026-07-01", "192.0.2.10", "evil.example", "a" * 64, "SHA256"],
            ["CVE-2026-0002 advisory", "Healthcare", "2026-07-02", "198.51.100.42", "ioc.example", "b" * 32, "MD5"],
        ],
        columns=TI_COLUMNS,
    )
    with_empty = pd.DataFrame(
        [
            ["CVE-2026-1000 advisory", "Energy", "2026-07-03", np.nan, "bad.example", "c" * 64, "SHA256"],
            ["CVE-2026-1001 advisory", np.nan, "2026-07-04", "203.0.113.5", np.nan, "d" * 40, "SHA1"],
            [np.nan, "Retail", np.nan, "203.0.113.8", "empty.example", np.nan, np.nan],
        ],
        columns=TI_COLUMNS,
    )
    paths = {
        "ti_full_xlsx": OUT_DIR / "threat_intel_exact_columns_full.xlsx",
        "ti_nan_xlsx": OUT_DIR / "threat_intel_exact_columns_with_empty_cells.xlsx",
        "qradar_csv": OUT_DIR / "qradar_upload_smoke.csv",
        "xsoar_csv": OUT_DIR / "xsoar_upload_smoke.csv",
        "threat_intel_csv": OUT_DIR / "threat_intel_upload_smoke.csv",
    }
    full.to_excel(paths["ti_full_xlsx"], index=False)
    with_empty.to_excel(paths["ti_nan_xlsx"], index=False)
    full.to_csv(paths["threat_intel_csv"], index=False)
    pd.DataFrame([{"offense_id": "O-1", "severity": 7, "status": "open"}]).to_csv(paths["qradar_csv"], index=False)
    pd.DataFrame([{"incident_id": "I-1", "playbook": "Containment", "analyst": "qa"}]).to_csv(paths["xsoar_csv"], index=False)
    return paths


def login():
    response = requests.post(f"{API_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(headers, source, path):
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if path.suffix == ".xlsx" else "text/csv"
    with path.open("rb") as fh:
        response = requests.post(
            f"{API_URL}/upload/data",
            params={"source": source},
            headers=headers,
            files={"file": (path.name, fh, mime)},
            timeout=30,
        )
    body_text = response.text[:1000]
    try:
        data = response.json()
    except Exception:
        data = {"raw": body_text}
    assert response.status_code == 200, f"{source} {path.name} returned {response.status_code}: {body_text}"
    assert response.status_code < 500, f"Unexpected 5xx for {source} {path.name}: {body_text}"
    assert isinstance(data.get("rows"), int), f"Missing integer rows in {data}"
    assert isinstance(data.get("columns"), list) and data["columns"], f"Missing columns in {data}"
    assert isinstance(data.get("sample"), list), f"Missing sample list in {data}"
    json.dumps(data, allow_nan=False)
    return data


def main():
    paths = write_files()
    headers = login()
    results = {}

    results["ti_full_xlsx"] = upload(headers, "threat_intel", paths["ti_full_xlsx"])
    assert results["ti_full_xlsx"]["columns"] == TI_COLUMNS, results["ti_full_xlsx"]["columns"]
    assert results["ti_full_xlsx"]["rows"] == 2, results["ti_full_xlsx"]

    results["ti_nan_xlsx"] = upload(headers, "threat_intel", paths["ti_nan_xlsx"])
    assert results["ti_nan_xlsx"]["columns"] == TI_COLUMNS, results["ti_nan_xlsx"]["columns"]
    assert results["ti_nan_xlsx"]["rows"] == 3, results["ti_nan_xlsx"]
    empty_values = [v for row in results["ti_nan_xlsx"]["sample"] for v in row.values() if v == ""]
    assert empty_values, f"Expected empty cells to be serialized as empty strings: {results['ti_nan_xlsx']['sample']}"

    results["csv_qradar"] = upload(headers, "qradar", paths["qradar_csv"])
    results["csv_xsoar"] = upload(headers, "xsoar", paths["xsoar_csv"])
    results["csv_threat_intel"] = upload(headers, "threat_intel", paths["threat_intel_csv"])

    print(json.dumps({"ok": True, "api_url": API_URL, "files": {k: str(v) for k, v in paths.items()}, "results": results}, indent=2))


if __name__ == "__main__":
    main()