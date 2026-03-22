const { test, expect } = require('@playwright/test');

test.describe('Phugoid Flight Dynamics Workbench', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('should load the page with correct title and initial state', async ({ page }) => {
        await expect(page).toHaveTitle('Phugoid - Flight Dynamics Workbench');

        // Check initial form values
        await expect(page.locator('#velocity')).toHaveValue('51.44');
        await expect(page.locator('#altitude')).toHaveValue('1524');

        // Check empty state is visible
        await expect(page.locator('#empty-state')).toBeVisible();
        await expect(page.locator('#results')).toBeHidden();
        await expect(page.locator('#visualization')).toBeHidden();
    });

    test('should update form values when presets are clicked', async ({ page }) => {
        const approachBtn = page.locator('button.preset-btn:has-text("Approach")');
        await approachBtn.click();

        await expect(page.locator('#velocity')).toHaveValue('33.4');
        await expect(page.locator('#altitude')).toHaveValue('300');

        const cruiseBtn = page.locator('button.preset-btn:has-text("Cruise")');
        await cruiseBtn.click();

        await expect(page.locator('#velocity')).toHaveValue('51.44');
        await expect(page.locator('#altitude')).toHaveValue('1524');
    });

    test('should handle unit toggle (Metric/Imperial)', async ({ page }) => {
        const toggle = page.locator('.switch');

        // Default is Metric (but displays the imperial equivalent in the hint)
        await expect(page.locator('#velocity-unit-display')).toContainText('kts');
        await expect(page.locator('#altitude-unit-display')).toContainText('ft');

        // Switch to Imperial
        await toggle.click();

        // Check form values converted to imperial (approx values)
        const vel = await page.locator('#velocity').inputValue();
        const alt = await page.locator('#altitude').inputValue();

        expect(Number(vel)).toBeCloseTo(100, 0); // ~100 kts
        expect(Number(alt)).toBeCloseTo(5000, -1); // ~5000 ft

        // Switch back to Metric
        await toggle.click();

        const velMetric = await page.locator('#velocity').inputValue();
        const altMetric = await page.locator('#altitude').inputValue();

        expect(Number(velMetric)).toBeCloseTo(51.44, 1);
        expect(Number(altMetric)).toBeCloseTo(1524, 0);
    });

    test('should calculate trim and stability when form is submitted', async ({ page }) => {
        // Intercept API calls to mock responses if necessary, or just rely on backend
        // Here we rely on the backend being up

        await page.locator('#calculate-btn').click();

        // Wait for results to be visible
        await expect(page.locator('#results')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('#empty-state')).toBeHidden();

        // Check trim results populated
        const trimAlpha = await page.locator('#trim-alpha').innerText();
        expect(trimAlpha).not.toBe('-');
        expect(Number(trimAlpha)).toBeGreaterThan(-20);
        expect(Number(trimAlpha)).toBeLessThan(20);

        const trimElevator = await page.locator('#trim-elevator').innerText();
        expect(trimElevator).not.toBe('-');

        // Check modes list populated
        await expect(page.locator('#lon-modes li').first()).toBeVisible({ timeout: 5000 });
        await expect(page.locator('#lat-modes li').first()).toBeVisible({ timeout: 5000 });
    });

    test('should run example analysis via Quick Start button', async ({ page }) => {
        await page.locator('#quick-start-btn').click();

        // Wait for results to be visible
        await expect(page.locator('#results')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('#empty-state')).toBeHidden();

        const trimAlpha = await page.locator('#trim-alpha').innerText();
        expect(trimAlpha).not.toBe('-');
    });

    test('should copy trim results to clipboard', async ({ page, context }) => {
        // Grant clipboard permissions
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);

        // Submit first to get results
        await page.locator('#calculate-btn').click();
        await expect(page.locator('#results')).toBeVisible({ timeout: 10000 });

        // Click copy button
        await page.locator('#copy-trim-btn').click();

        // Read clipboard
        const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
        expect(clipboardText).toContain('Trim State:');
        expect(clipboardText).toContain('Alpha:');
        expect(clipboardText).toContain('Elevator:');
    });

    test('should handle validation errors', async ({ page }) => {
        await page.locator('#velocity').fill('-10'); // Invalid velocity
        await page.locator('#calculate-btn').click();

        // Native HTML5 validation should prevent submission, or show error message
        // This checks if the form is still invalid or an error message is shown
        const errorMessage = page.locator('#error-message');

        // If the custom validation is triggered
        const isValid = await page.locator('#velocity').evaluate(node => node.checkValidity());
        expect(isValid).toBe(false);
    });
});
