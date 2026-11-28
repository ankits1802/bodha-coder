import { expect, test } from "@playwright/test";
import { VERIFY_TEXT } from "../../src/features/verify/strings";
import { expectAccessible } from "../support/accessibility";
import { heading } from "../support/app";
import { seed } from "../support/seed";

interface VerifyDay {
  code: string;
  practice: string;
  signer: string;
}

test("anyone can verify the seal of an approved claim on the public verify page", async ({ page }) => {
  const day = await seed<VerifyDay>("verify-day");
  await page.goto("/verify");
  await expect(heading(page, VERIFY_TEXT.title)).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("textbox", { name: VERIFY_TEXT.code }).fill(day.code);
  await page.getByRole("button", { name: VERIFY_TEXT.verify, exact: true }).click();
  const result = page.getByRole("region", { name: VERIFY_TEXT.resultLabel });
  await expect(result.getByRole("status")).toHaveText(VERIFY_TEXT.valid);
  await expect(result).toContainText(VERIFY_TEXT.events.approval);
  await expect(result).toContainText(day.practice);
  await expect(result).toContainText(day.signer);
  await expect(page).toHaveURL(new RegExp("/verify\\?code="));
  await expectAccessible(page);
});
