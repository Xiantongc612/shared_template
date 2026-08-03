import { expect, test } from "@playwright/test";

test("shows the desktop workspace", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});
