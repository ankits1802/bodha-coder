import { expect, test } from "@playwright/test";
import { SET_PASSWORD_TEXT } from "../../src/features/set-password/strings";
import { SIGN_IN_TEXT } from "../../src/features/sign-in/strings";
import { SIGN_UP_TEXT } from "../../src/features/sign-up/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { expectAccessible } from "../support/accessibility";
import { EMAIL_DOMAIN, heading, marker, skipTour } from "../support/app";
import { linkIn, nextMessage } from "../support/mailbox";
import { enterCode } from "../support/signIn";
import { totpCode } from "../support/totp";

test("a new practice signs up, verifies its email, agrees and lands on Today", async ({ page }) => {
  const run = marker();
  const email = `owner-${run}@${EMAIL_DOMAIN}`;
  const practice = `Synthetic Family Clinic ${run.toUpperCase()}`;
  const password = `Synthetic-${run}-password`;

  await page.goto("/sign-up");
  await expect(page.getByRole("heading", { name: SIGN_UP_TEXT.title })).toBeVisible();
  await expectAccessible(page);
  await page.getByLabel(SIGN_UP_TEXT.name).fill("Riley Owner");
  await page.getByLabel(SIGN_UP_TEXT.practiceName).fill(practice);
  await page.getByLabel(SIGN_UP_TEXT.email).fill(email);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: SIGN_UP_TEXT.create }).click();
  await expect(page.getByRole("heading", { name: SIGN_UP_TEXT.checkEmailTitle })).toBeVisible();

  const invite = await nextMessage(email, (message) => message.subject === `Join ${practice} on Bodha Assure`);
  await page.goto(linkIn(invite, "/set-password"));
  await expect(page.getByRole("heading", { name: SET_PASSWORD_TEXT.title })).toBeVisible();
  await expectAccessible(page);
  await page.getByLabel(SET_PASSWORD_TEXT.password, { exact: true }).fill(password);
  await page.getByLabel(SET_PASSWORD_TEXT.confirm, { exact: true }).fill(password);
  await page.getByRole("button", { name: SET_PASSWORD_TEXT.submit }).click();

  await expect(page.getByRole("heading", { name: SIGN_IN_TEXT.setupTitle })).toBeVisible();
  await expectAccessible(page);
  const key = page.getByText(SIGN_IN_TEXT.secretLabel, { exact: true }).locator("xpath=following-sibling::span[1]");
  const secret = ((await key.textContent()) ?? "").replace(/\s+/g, "");
  await enterCode(page, totpCode(secret));
  await expect(page.getByRole("heading", { name: SIGN_IN_TEXT.codesTitle })).toBeVisible();
  await page.getByRole("button", { name: SIGN_IN_TEXT.continue }).click();

  await skipTour(page);
  await expect(heading(page, TODAY_TEXT.title)).toBeVisible();
  await expect(page.getByRole("region", { name: TODAY_TEXT.checklist.title })).toBeVisible();
  await expectAccessible(page);
});
