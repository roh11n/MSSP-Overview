"""
Focused Playwright script for the Threat Intel Excel upload bug.

This file mirrors the script passed to mcp_browser_automation, which runs the
content inside an async function with a `page` object already available.
"""

await page.set_viewport_size({"width": 1920, "height": 1080})
try:
    print("Step 1: open app and authenticate as admin")
    await page.goto(page.url if page.url != "about:blank" else "https://audience-first-dash.preview.emergentagent.com", wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)
    if await page.get_by_test_id("login-form").is_visible(timeout=5000):
        await page.get_by_test_id("login-email").fill("admin@mssp-soc.io")
        await page.get_by_test_id("login-password").fill("Admin@2026!")
        await page.get_by_test_id("login-submit").click()
        print("Login submitted")
    await page.get_by_test_id("header-upload-btn").wait_for(state="visible", timeout=20000)
    print("Authenticated and dashboard header is visible")

    async def upload_file_and_verify(file_path, expected_rows, expected_filename):
        print(f"Step 2: open upload modal for {expected_filename}")
        await page.get_by_test_id("header-upload-btn").click()
        await page.get_by_test_id("upload-modal").wait_for(state="visible", timeout=10000)
        await page.get_by_test_id("upload-source-select").click()
        await page.wait_for_timeout(200)
        await page.get_by_role("option", name="Threat Intel (Advisories / CVE / IOC)").click(force=True)
        print("Threat Intel source selected")

        await page.get_by_test_id("upload-file-input").set_input_files(file_path)
        await page.get_by_text(expected_filename, exact=True).wait_for(state="visible", timeout=10000)
        print("Excel file attached")

        async with page.expect_response(lambda r: "/api/upload/data" in r.url and "source=threat_intel" in r.url, timeout=30000) as response_info:
            await page.get_by_test_id("upload-submit-btn").click()
        response = await response_info.value
        status = response.status
        response_json = await response.json()
        print(f"Upload API response status={status}, rows={response_json.get('rows')}, columns={response_json.get('columns')}")
        assert status == 200, f"Expected 200 upload response, got {status}: {response_json}"
        assert response_json.get("rows") == expected_rows, f"Unexpected row count: {response_json}"
        assert response_json.get("columns")[:7] == ["Advisories Name ", "Industry", "Date of Release", "IPs ", "Domain", "Hash", "Hash Type"], response_json.get("columns")
        assert isinstance(response_json.get("sample"), list), f"Missing sample: {response_json}"

        await page.get_by_text("Ingestion complete", exact=True).wait_for(state="visible", timeout=10000)
        await page.get_by_text(f"Rows: {expected_rows}").wait_for(state="visible", timeout=10000)
        await page.get_by_text(f"Ingested {expected_rows} rows from {expected_filename}").wait_for(state="visible", timeout=10000)
        print("Success card and toast verified")

        error_text = await page.evaluate("""() => {
const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
return errorElements.map(el => el.textContent).join(", ");
}""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")
        assert "Upload failed" not in await page.locator("body").inner_text(), "Upload failed text is visible after successful upload"

        await page.get_by_test_id("upload-cancel-btn").click()
        await page.wait_for_timeout(500)

    await upload_file_and_verify("/app/test_reports/upload_artifacts/threat_intel_exact_columns_full.xlsx", 2, "threat_intel_exact_columns_full.xlsx")
    await upload_file_and_verify("/app/test_reports/upload_artifacts/threat_intel_exact_columns_with_empty_cells.xlsx", 3, "threat_intel_exact_columns_with_empty_cells.xlsx")
    print("PASS: Threat Intel Excel upload succeeds in UI for exact columns and empty cells")
except Exception as exc:
    print(f"FAIL: {exc}")
    await page.screenshot(path="/app/test_reports/upload_artifacts/threat_intel_upload_ui_failure.jpg", quality=40, full_page=False)
    raise