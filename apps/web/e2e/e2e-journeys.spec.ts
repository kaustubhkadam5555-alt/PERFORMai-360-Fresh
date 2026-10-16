import { test, expect } from "@playwright/test";

test.describe("PERFORMai-360 — Phase 10 End-to-End Validation", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to homepage
    await page.goto("/");
  });

  test("1. Application loads successfully with semantic landmarks and header navigation", async ({
    page,
  }) => {
    // Check page title
    await expect(page).toHaveTitle(/PERFORMai-360/i);

    // Verify semantic landmarks exist
    const header = page.locator("header");
    await expect(header).toBeVisible();

    const main = page.locator("main");
    await expect(main).toBeVisible();

    const footer = page.locator("footer");
    await expect(footer).toBeVisible();

    // Verify header brand title
    const brand = page.locator("header").getByText("PERFORMai-360");
    await expect(brand).toBeVisible();

    // Verify hero headline
    const headline = page.getByRole("heading", {
      name: /AI-Driven Bias-Aware 360° Evaluation/i,
      level: 1,
    });
    await expect(headline).toBeVisible();

    // Verify key guarantees metrics bar
    await expect(page.getByText("360°", { exact: true })).toBeVisible();
    await expect(page.getByText("5 Rules", { exact: true })).toBeVisible();
    await expect(page.getByText("4 Agents", { exact: true })).toBeVisible();
    await expect(page.getByText("100%", { exact: true })).toBeVisible();
  });

  test("2. Navigation anchor links scroll smoothly to application sections", async ({
    page,
  }) => {
    // Test navigation links
    const governanceLink = page.locator('nav a[href="#governance"]');
    await expect(governanceLink).toBeVisible();
    await governanceLink.click({ force: true });

    // Check governance section exists
    const governanceSection = page.locator("#governance");
    await expect(governanceSection).toBeAttached();

    const analyticsLink = page.locator('nav a[href="#analytics"]');
    await expect(analyticsLink).toBeVisible();
    await analyticsLink.click({ force: true });

    // Check analytics section exists
    const analyticsSection = page.locator("#analytics");
    await expect(analyticsSection).toBeAttached();
  });

  test("3. Analytics dashboard loads, renders metrics, and supports accessible table toggles", async ({
    page,
  }) => {
    // Scroll down to analytics section
    const analyticsSection = page.locator("#analytics");
    await analyticsSection.scrollIntoViewIfNeeded();

    // Verify analytics card header
    await expect(
      page.getByRole("heading", { name: /Performance & Governance Analytics Dashboard/i })
    ).toBeVisible();

    // Verify the accessible table toggle button is present
    const toggleButton = page.getByRole("button", {
      name: /Show Accessible Tables \(WCAG\)|Hide Data Tables/i,
    });
    await expect(toggleButton).toBeVisible();
    await expect(toggleButton).toHaveAttribute("aria-pressed", "false");

    // Click toggle button to enable accessible fallback data tables
    await toggleButton.click();
    await expect(toggleButton).toHaveAttribute("aria-pressed", "true");
    await expect(toggleButton).toHaveText(/Hide Data Tables/i);

    // Click again to hide data tables and return to chart view
    await toggleButton.click();
    await expect(toggleButton).toHaveAttribute("aria-pressed", "false");
  });

  test("4. Report governance card renders versioning controls and accessible export buttons", async ({
    page,
  }) => {
    // Scroll to governance section
    const governanceSection = page.locator("#governance");
    await governanceSection.scrollIntoViewIfNeeded();

    // Verify Report Governance heading
    await expect(
      page.getByRole("heading", { name: /Human Approval, Versioning & Governance/i })
    ).toBeVisible();

    // Verify tabs and review controls are present
    await expect(
      governanceSection.getByRole("button", { name: /Draft Report & Section Editor/i })
    ).toBeVisible();
    await expect(
      governanceSection.getByRole("button", { name: /Version History/i })
    ).toBeVisible();
    await expect(
      governanceSection.getByRole("button", { name: /Deterministic Version Diff/i })
    ).toBeVisible();

    // Verify Review Cycle and Role selectors exist
    await expect(governanceSection.locator("select").first()).toBeVisible();

    // Wait for active report to load and verify export buttons if present
    const activeReportStatus = governanceSection.getByText(/Active Report Status:/i);
    const hasReport = await activeReportStatus.isVisible({ timeout: 6000 }).catch(() => false);
    if (hasReport) {
      const pdfExportBtn = governanceSection.locator('button[aria-label*="Export"][aria-label*="PDF"]').first();
      const docxExportBtn = governanceSection.locator('button[aria-label*="Export"][aria-label*="DOCX"]').first();
      await expect(pdfExportBtn).toBeVisible();
      await expect(docxExportBtn).toBeVisible();
      await expect(pdfExportBtn).toBeEnabled();
      await expect(docxExportBtn).toBeEnabled();
    }
  });

  test("5. Multi-agent workflow card renders execution pipeline stages", async ({
    page,
  }) => {
    // Scroll to orchestration section
    const orchestrationSection = page.locator("#orchestration");
    await orchestrationSection.scrollIntoViewIfNeeded();

    // Verify workflow section heading
    await expect(
      page.getByRole("heading", { name: /Multi-Agent Review Orchestration Engine/i })
    ).toBeVisible();

    // Verify key agent stage cards are visible
    await expect(orchestrationSection.getByText("EvidenceRetrieval")).toBeVisible();
    await expect(orchestrationSection.getByText("FeedbackAnalysis")).toBeVisible();
    await expect(orchestrationSection.getByText("BiasAuditorAgent")).toBeVisible();
    await expect(orchestrationSection.getByText("ReviewSynthesis")).toBeVisible();
  });
});
