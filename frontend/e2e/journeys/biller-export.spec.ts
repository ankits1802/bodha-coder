import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { BILLING_TEXT } from "../../src/features/billing/strings";
import { expectAccessible } from "../support/accessibility";
import { heading } from "../support/app";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface BillerDay {
  biller: Account;
  patients: string[];
}

const CSV_HEADER = "note_id,patient,service_date,place_of_service";

test("a biller exports the approved visits as claim lines in CSV", async ({ page }) => {
  const day = await seed<BillerDay>("biller-day");
  await signIn(page, day.biller);
  await expect(heading(page, BILLING_TEXT.title)).toBeVisible();
  const visits = page.getByRole("table", { name: BILLING_TEXT.tableLabel });
  for (const patient of day.patients) await expect(visits).toContainText(patient);
  await expect(page.getByRole("combobox", { name: BILLING_TEXT.claimLines.format })).toHaveText(BILLING_TEXT.claimLines.formats.csv);
  await expectAccessible(page);

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: BILLING_TEXT.claimLines.export(String(day.patients.length)) }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(new RegExp("^bodha-claim-lines-.*\\.csv$"));
  const csv = await readFile(await file.path(), "utf8");
  expect(csv.startsWith(CSV_HEADER)).toBe(true);
  for (const patient of day.patients) expect(csv).toContain(patient);
  await expect(page.getByRole("status").filter({ hasText: BILLING_TEXT.exported(String(day.patients.length)) })).toBeVisible();
});
