import { expect, test } from "@playwright/test";
import { SHARED_TEXT } from "../../src/components/shared/strings";
import { HQ_TEXT } from "../../src/features/hq/strings";
import { expectAccessible } from "../support/accessibility";
import { ADMIN_ORIGIN, heading } from "../support/app";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface HqDay {
  hq: Account;
  practice: { id: string; name: string };
}

const renewal = HQ_TEXT.practices.renewal;

test.use({ baseURL: ADMIN_ORIGIN });

test("HQ signs in with two-step on its own host, finds a practice, opens it and renews it", async ({ page }) => {
  const day = await seed<HqDay>("hq-day");
  await signIn(page, day.hq);
  await expect(heading(page, HQ_TEXT.overview.title)).toBeVisible();
  expect(new URL(page.url()).host).toBe(new URL(ADMIN_ORIGIN).host);
  await expectAccessible(page);

  await page.getByRole("link", { name: new RegExp(`^${HQ_TEXT.overview.practices}, `) }).click();
  await expect(page).toHaveURL(/\/hq\/practices\?status=live$/);
  await expect(heading(page, HQ_TEXT.practices.title)).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("link", { name: day.practice.name, exact: true }).click();
  await expect(heading(page, day.practice.name)).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/hq/practices/${day.practice.id}`));
  await expectAccessible(page);

  await page.getByRole("button", { name: HQ_TEXT.practice.renew, exact: true }).click();
  const dialog = page.getByRole("dialog", { name: renewal.title(day.practice.name) });
  await dialog.getByRole("radio", { name: renewal.presets.month3, exact: true }).check({ force: true });
  await expectAccessible(page);
  await dialog.getByRole("button", { name: renewal.action, exact: true }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("status").filter({ hasText: day.practice.name })).toBeVisible();

  await page.getByRole("button", { name: SHARED_TEXT.nav.search, exact: true }).click();
  const search = page.getByRole("dialog", { name: HQ_TEXT.search.title });
  await search.getByRole("combobox", { name: HQ_TEXT.search.label }).fill(day.practice.name);
  await search.getByRole("option").filter({ hasText: day.practice.name }).first().click();
  await expect(search).toBeHidden();
  await expect(heading(page, day.practice.name)).toBeVisible();
});
