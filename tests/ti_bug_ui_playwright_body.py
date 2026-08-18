"""Playwright body used by browser automation for TI dashboard KPI verification.

It logs in as admin, opens the Threat Intelligence dashboard, switches all
period tabs, and checks the Total Advisories KPI remains 60.
"""

BASE_URL = "https://audience-first-dash.preview.emergentagent.com"

await page.set_viewport_size({"width": 1920, "height": 1080})
try:
    print("Opening login page")
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")

    if await page.get_by_test_id("login-submit").is_visible(timeout=5000):
        await page.get_by_test_id("login-email").fill("admin@mssp-soc.io")
        await page.get_by_test_id("login-password").fill("Admin@2026!")
        await page.get_by_test_id("login-submit").click()
        await page.wait_for_timeout(1500)
        print("Login submitted")

    await page.goto(f"{BASE_URL}/threat-intel")
    await page.wait_for_load_state("networkidle")
    await page.get_by_test_id("threat-intel-page").wait_for(state="visible", timeout=15000)
    await page.get_by_test_id("kpi-total-advisories").wait_for(state="visible", timeout=20000)
    await page.get_by_test_id("ti-data-source-chip").wait_for(state="visible", timeout=10000)
    chip_text = await page.get_by_test_id("ti-data-source-chip").text_content()
    print(f"Data source chip: {chip_text}")

    results = {}
    for period, tab_testid in [("monthly", "tab-monthly"), ("weekly", "tab-weekly"), ("quarterly", "tab-quarterly")]:
        print(f"Selecting {period} tab")
        await page.get_by_test_id(tab_testid).click(force=True)
        await page.wait_for_timeout(1200)
        await page.get_by_test_id("kpi-total-advisories").wait_for(state="visible", timeout=10000)
        text = await page.get_by_test_id("kpi-total-advisories").text_content()
        results[period] = text
        print(f"{period} Total Advisories card text: {text}")
        await page.screenshot(path=f"/app/test_reports/ti_ui_{period}.jpg", quality=40, full_page=False)

    # Get error messages using specific selectors
    error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")

    bad = {k: v for k, v in results.items() if "60" not in (v or "")}
    if bad:
        raise Exception(f"Total Advisories did not show 60 for all tabs: {bad}")
    if "Welspun_July_2026.xlsx" not in (chip_text or ""):
        raise Exception(f"Data source chip did not show expected filename: {chip_text}")
    print(f"UI KPI verification passed: {results}")
except Exception as exc:
    print(f"UI KPI verification failed: {exc}")
    await page.screenshot(path="/app/test_reports/ti_ui_failure.jpg", quality=40, full_page=False)
    raise