import { expect, test, type Page } from "@playwright/test";
import { HELP_TEXT } from "../../src/features/help/strings";
import { HQ_TEXT } from "../../src/features/hq/strings";
import { INSIGHTS_TEXT } from "../../src/features/insights/strings";
import { PLAN_TEXT } from "../../src/features/plan/strings";
import { SECURITY_TEXT } from "../../src/features/security/strings";
import { SETUP_TEXT } from "../../src/features/setup/strings";
import { TEAM_TEXT } from "../../src/features/team/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { signIn } from "../support/signIn";
import { keepReadOnly, setting } from "./readOnly";

const SITE_URL = process.env.CANARY_SITE_URL || "https://www.bodhaai.co";
const ADMIN_URL = process.env.CANARY_ADMIN_URL || "https://admin.bodhaai.co";

const PRACTICE_PAGES: readonly [string, string][] = [
  ["/today", TODAY_TEXT.title],
  ["/insights", INSIGHTS_TEXT.title],
  ["/settings/setup", SETUP_TEXT.title],
  ["/settings/team", TEAM_TEXT.title],
  ["/settings/plan", PLAN_TEXT.title],
  ["/settings/security", SECURITY_TEXT.title],
  ["/account", SECURITY_TEXT.accountTitle],
  ["/help", HELP_TEXT.title],
];

const HQ_PAGES: readonly [string, string][] = [
  ["/hq", HQ_TEXT.overview.title],
  ["/hq/practices", HQ_TEXT.practices.title],
  ["/hq/organizations", HQ_TEXT.organizations.title],
  ["/hq/activity", HQ_TEXT.activity.title],
  ["/hq/spend", HQ_TEXT.spend.title],
  ["/hq/team", HQ_TEXT.team.title],
  ["/hq/demos", HQ_TEXT.demos.title],
];

async function walk(page: Page, origin: string, pages: readonly [string, string][]): Promise<void> {
  for (const [path, heading] of pages) {
    await test.step(path, async () => {
      await page.goto(`${origin}${path}`);
      await expect(page.getByRole("heading", { level: 1, name: heading, exact: true })).toBeVisible();
    });
  }
}

test("the API answers ready on both hosts", async ({ request }) => {
  for (const origin of [SITE_URL, ADMIN_URL]) {
    const response = await request.get(`${origin}/api/health/ready`);
    expect(response.status(), `${origin}/api/health/ready`).toBe(200);
    expect((await response.json()).status).toBe("ready");
  }
});

test("the practice canary signs in and opens the practice pages", async ({ page }) => {
  const problems = await keepReadOnly(page);
  await signIn(
    page,
    {
      email: setting("CANARY_PRACTICE_EMAIL"),
      password: setting("CANARY_PRACTICE_PASSWORD"),
      two_step_secret: setting("CANARY_PRACTICE_TOTP_SECRET"),
    },
    SITE_URL,
  );
  await expect(page.getByRole("heading", { level: 1, name: TODAY_TEXT.title, exact: true })).toBeVisible();
  await walk(page, SITE_URL, PRACTICE_PAGES);
  expect(problems).toEqual({ refused: [], failed: [] });
});

test("the HQ canary signs in on the admin host and opens the HQ pages", async ({ page }) => {
  const problems = await keepReadOnly(page);
  await signIn(
    page,
    {
      email: setting("CANARY_HQ_EMAIL"),
      password: setting("CANARY_HQ_PASSWORD"),
      two_step_secret: setting("CANARY_HQ_TOTP_SECRET"),
    },
    ADMIN_URL,
  );
  await expect(page.getByRole("heading", { level: 1, name: HQ_TEXT.overview.title, exact: true })).toBeVisible();
  await walk(page, ADMIN_URL, HQ_PAGES);
  expect(problems).toEqual({ refused: [], failed: [] });
});
