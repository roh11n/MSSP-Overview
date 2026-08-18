#!/usr/bin/env python3
"""Focused backend verification for threat-intel advisory count regression.

This script logs in, re-uploads the Welspun July 2026 threat-intel workbook,
and verifies that the dashboard API reports the full uploaded batch count for
weekly/monthly/quarterly periods.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests


BASE_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8001/api")
EMAIL = os.environ.get("TEST_EMAIL", "admin@mssp-soc.io")
PASSWORD = os.environ.get("TEST_PASSWORD", "Admin@2026!")
TENANT_ID = os.environ.get("TENANT_ID", "all")
FILE_PATH = Path(os.environ.get("TI_FILE", "/tmp/welspun.xlsx"))
REPORT_PATH = Path("/app/test_reports/ti_backend_evidence.json")


def fail(message, evidence=None):
    payload = {"ok": False, "error": message, "evidence": evidence or {}}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2, default=str))
    print(json.dumps(payload, indent=2, default=str))
    sys.exit(1)


def main():
    if not FILE_PATH.exists():
        fail(f"Required workbook not found: {FILE_PATH}")

    # Independent sanity check of the workbook's advisory uniqueness.
    df = pd.read_excel(FILE_PATH)
    normalised_columns = {str(c).strip().lower(): c for c in df.columns}
    advisory_col = normalised_columns.get("advisories name") or normalised_columns.get("advisory")
    if advisory_col is None:
        fail("Workbook does not contain an advisory name column", {"columns": list(df.columns)})
    expected_unique_advisories = int(df[advisory_col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique())

    session = requests.Session()
    login_res = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    if login_res.status_code != 200:
        fail("Login failed", {"status": login_res.status_code, "body": login_res.text[:500]})
    token = login_res.json().get("access_token")
    if not token:
        fail("Login response did not include access_token", login_res.json())
    session.headers.update({"Authorization": f"Bearer {token}"})

    with FILE_PATH.open("rb") as fh:
        upload_res = session.post(
            f"{BASE_URL}/upload/data",
            params={"source": "threat_intel", "tenant_id": TENANT_ID},
            files={"file": ("Welspun_July_2026.xlsx", fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=60,
        )
    if upload_res.status_code != 200:
        fail("Threat-intel upload failed", {"status": upload_res.status_code, "body": upload_res.text[:1000]})
    upload_json = upload_res.json()

    period_results = {}
    failures = []
    for period in ["weekly", "monthly", "quarterly"]:
        res = session.get(
            f"{BASE_URL}/dashboard/threat-intel",
            params={"tenant_id": TENANT_ID, "period": period},
            timeout=30,
        )
        if res.status_code != 200:
            failures.append(f"{period}: status {res.status_code}, body {res.text[:500]}")
            continue
        data = res.json()
        summary = data.get("summary", {})
        period_results[period] = {
            "data_status": data.get("data_status"),
            "upload": data.get("upload"),
            "summary": summary,
            "timeline_points": len(data.get("advisories_timeline") or []),
        }

        if data.get("data_status") != "live":
            failures.append(f"{period}: data_status expected live, got {data.get('data_status')}")
        if (data.get("upload") or {}).get("filename") != "Welspun_July_2026.xlsx":
            failures.append(f"{period}: upload filename mismatch: {(data.get('upload') or {}).get('filename')}")
        if summary.get("total_advisories") != 60:
            failures.append(f"{period}: total_advisories expected 60, got {summary.get('total_advisories')}")
        if summary.get("total_advisories") != expected_unique_advisories:
            failures.append(f"{period}: total_advisories {summary.get('total_advisories')} != workbook unique advisory count {expected_unique_advisories}")
        if not (summary.get("unique_domains", 0) > 300):
            failures.append(f"{period}: unique_domains expected >300, got {summary.get('unique_domains')}")
        if not (summary.get("unique_hashes", 0) > 500):
            failures.append(f"{period}: unique_hashes expected >500, got {summary.get('unique_hashes')}")
        if not (summary.get("unique_ips", 0) > 100):
            failures.append(f"{period}: unique_ips expected >100, got {summary.get('unique_ips')}")
        if not (summary.get("industries_covered", 0) >= 7):
            failures.append(f"{period}: industries_covered expected >=7, got {summary.get('industries_covered')}")

    evidence = {
        "base_url": BASE_URL,
        "file": str(FILE_PATH),
        "workbook_rows": int(len(df)),
        "workbook_unique_advisories": expected_unique_advisories,
        "upload_response": upload_json,
        "period_results": period_results,
        "failures": failures,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps({"ok": not failures, "evidence": evidence}, indent=2, default=str))
    print(json.dumps({"ok": not failures, "evidence": evidence}, indent=2, default=str))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()