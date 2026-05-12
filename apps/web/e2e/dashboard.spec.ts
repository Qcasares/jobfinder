import { expect, test } from "@playwright/test";

test.describe("Jobfinder dashboard", () => {
  test("keeps the job-search overview focused on user outcomes", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", { level: 2, name: "Job Search Overview" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Set up automated job search in three steps" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Search Readiness" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Shortlist Review" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Trust Controls" })).toBeVisible();
    await expect(
      page.getByText(/Live data synced|Preview data loaded|Results may be delayed/).first()
    ).toBeVisible();
    await expect(page.getByText("API Health")).toHaveCount(0);
  });

  test("routes setup and keeps locked next steps explicit", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: /Set up automated search/ }).click();
    await expect(page.getByRole("heading", { name: "Profile and preferences" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Job Preferences" })).toBeVisible();

    await page.getByRole("button", { name: "Overview" }).click();
    await expect(page.getByRole("button", { name: /Get recommendations/ })).toBeDisabled();
    await expect(page.getByRole("button", { name: /Review shortlist/ })).toBeDisabled();

    await page.getByRole("button", { name: "Jobs" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Live Jobs" })).toBeVisible();

    await page.getByRole("button", { name: "Reviews Needed" }).click();
    await expect(page.getByRole("heading", { level: 1, name: /Reviews needed/i })).toBeVisible();
  });

  test("keeps technical health diagnostics inside administration", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("API Health")).toHaveCount(0);

    await page.getByRole("button", { name: /Administration/ }).click();

    await expect(page.getByText(/API Health:/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Health / API Status" })).toBeVisible();
    await expect(page.getByText("Preview data loaded")).toHaveCount(0);
  });
});
