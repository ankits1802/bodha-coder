import { expect, type Page } from "@playwright/test";
import { SIGN_IN_TEXT } from "../../src/features/sign-in/strings";
import { totpCode } from "./totp";

export interface Credentials {
  email: string;
  password: string;
  two_step_secret?: string | null;
}

export async function enterCode(page: Page, code: string): Promise<void> {
  await page.getByLabel(SIGN_IN_TEXT.digitLabel(1)).fill(code);
  await page.getByRole("button", { name: SIGN_IN_TEXT.verify }).click();
}

export async function signIn(page: Page, credentials: Credentials, origin = ""): Promise<void> {
  await page.goto(`${origin}/sign-in`);
  await page.getByLabel(SIGN_IN_TEXT.email, { exact: true }).fill(credentials.email);
  await page.getByLabel(SIGN_IN_TEXT.password, { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: SIGN_IN_TEXT.continue }).click();
  if (!credentials.two_step_secret) return;
  await expect(page.getByRole("heading", { name: SIGN_IN_TEXT.verifyTitle })).toBeVisible();
  await enterCode(page, totpCode(credentials.two_step_secret));
}
