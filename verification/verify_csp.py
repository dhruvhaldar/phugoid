from playwright.sync_api import sync_playwright, expect
import sys

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Capture console logs to check for CSP errors
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    try:
        # Navigate to homepage
        page.goto("http://127.0.0.1:8000/")

        # Verify page title
        expect(page).to_have_title("Phugoid - Flight Dynamics Workbench")
        print("Page loaded successfully.")

        # Fill inputs (using defaults) and submit
        # The form has defaults, so we can just click submit
        # But let's verify inputs exist first
        expect(page.locator("#velocity")).to_have_value("51.44")
        expect(page.locator("#altitude")).to_have_value("1524")

        # Click calculate
        page.click("#calculate-btn")
        print("Clicked Calculate button.")

        # Wait for results
        # We expect the trim results to be populated (initially '-', then numbers)
        # We can wait for one of the result spans to not be '-'
        expect(page.locator("#trim-alpha")).not_to_have_text("-", timeout=10000)
        print("Trim results populated.")

        # Check for mode list items
        expect(page.locator("#lon-modes li").first).to_be_visible()
        print("Longitudinal modes populated.")

        # Take screenshot
        page.screenshot(path="verification/verification.png", full_page=True)
        print("Screenshot taken.")

        # Check for CSP errors in console
        for err in console_errors:
            if "Content Security Policy" in err:
                print(f"CSP Error found: {err}")
                # We expect NO CSP errors for script-src
                if "script-src" in err:
                    raise Exception(f"CSP Script Violation: {err}")
            else:
                print(f"Console Error: {err}")

    except Exception as e:
        print(f"Verification failed: {e}")
        # Take screenshot on failure too
        page.screenshot(path="verification/failure.png", full_page=True)
        sys.exit(1)
    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
