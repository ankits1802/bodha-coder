import { randomBytes } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import { TOUR_TEXT } from "../../src/components/shared/tour/strings";

export const EMAIL_DOMAIN = "e2e.example.com";
export const ADMIN_ORIGIN = process.env.ADMIN_URL ?? "http://admin.localhost:3000";

export function marker(): string {
  return randomBytes(3).toString("hex");
}

export function heading(page: Page, name: string) {
  return page.getByRole("heading", { level: 1, name, exact: true });
}

export async function otherPerson(browser: Browser): Promise<Page> {
  const { baseURL, timezoneId, locale, viewport } = test.info().project.use;
  const context = await browser.newContext({ baseURL, timezoneId, locale, viewport });
  return context.newPage();
}

export async function untilShown(page: Page, check: () => Promise<void>, timeout = 90_000): Promise<void> {
  await expect(async () => {
    await page.reload();
    await check();
  }).toPass({ timeout });
}

export async function skipTour(page: Page): Promise<void> {
  const tour = page.getByRole("dialog", { name: TOUR_TEXT.welcome.practice.title });
  await expect(tour).toBeVisible();
  await tour.getByRole("button", { name: TOUR_TEXT.skip }).click();
  await expect(tour).toBeHidden();
}
