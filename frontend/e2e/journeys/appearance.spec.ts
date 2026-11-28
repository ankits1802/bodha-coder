import { expect, test, type Page } from "@playwright/test";
import { SECURITY_TEXT } from "../../src/features/security/strings";
import { APPEARANCE_COOKIE } from "../../src/lib/appearance";
import { expectAccessible } from "../support/accessibility";
import { heading } from "../support/app";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface AdminDay {
  admin: Account;
  practice: string;
}

const words = SECURITY_TEXT.appearance;
const APPEARANCE_PATH = "/api/auth/appearance";

async function choose(page: Page, group: string, option: string): Promise<void> {
  const saved = page.waitForResponse(
    (response) => new URL(response.url()).pathname === APPEARANCE_PATH && response.request().method() === "PUT" && response.ok(),
  );
  const panel = page.getByRole("region", { name: words.title });
  await panel.getByRole("radiogroup", { name: group }).getByRole("radio", { name: option, exact: true }).click();
  await saved;
}

test("a person's appearance applies at once, is kept for them and paints before the page shows", async ({ page, context }) => {
  const { admin } = await seed<AdminDay>("admin-day");
  await signIn(page, admin);
  await expect(page).not.toHaveURL(/\/sign-in/);
  await page.goto("/account");
  await expect(heading(page, SECURITY_TEXT.accountTitle)).toBeVisible();
  const root = page.locator("html");
  const body = page.locator("body");
  expect(await root.getAttribute("data-theme")).toBeNull();
  await expect(body).toHaveCSS("font-size", "14px");

  await choose(page, words.theme, words.themes.dark);
  await expect(root).toHaveAttribute("data-theme", "dark");
  await expect(body).toHaveCSS("background-color", "rgb(17, 17, 19)");
  await choose(page, words.textSize, words.textSizes.larger);
  await expect(root).toHaveAttribute("data-text-size", "larger");
  await expect(body).toHaveCSS("font-size", "17.5px");
  await choose(page, words.motion, words.motions.on);
  await expect(root).toHaveAttribute("data-motion", "reduce");
  await expectAccessible(page);

  await context.clearCookies({ name: APPEARANCE_COOKIE });
  await page.reload();
  await expect(heading(page, SECURITY_TEXT.accountTitle)).toBeVisible();
  await expect(root).toHaveAttribute("data-theme", "dark");
  await expect(root).toHaveAttribute("data-text-size", "larger");
  await expect(root).toHaveAttribute("data-motion", "reduce");
  await expect.poll(async () => (await context.cookies()).find((cookie) => cookie.name === APPEARANCE_COOKIE)?.value).toBe("dark.larger.on");

  const landing = await page.goto("/");
  const html = (await landing?.text()) ?? "";
  expect(html).toMatch(/<html[^>]*\sdata-theme="dark"/);
  expect(html).toMatch(/<html[^>]*\sdata-text-size="larger"/);
  expect(html).toMatch(/<html[^>]*\sdata-motion="reduce"/);
});
