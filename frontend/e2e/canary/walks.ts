import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { HELP_TEXT } from "../../src/features/help/strings";
import { HQ_TEXT } from "../../src/features/hq/strings";
import { INSIGHTS_TEXT } from "../../src/features/insights/strings";
import { PLAN_TEXT } from "../../src/features/plan/strings";
import { SECURITY_TEXT } from "../../src/features/security/strings";
import { SETUP_TEXT } from "../../src/features/setup/strings";
import { TEAM_TEXT } from "../../src/features/team/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { signIn, type Credentials } from "../support/signIn";
import { keepReadOnly } from "./readOnly";

type Walk = readonly [path: string, heading: string][];
type PageCheck = (page: Page) => Promise<void>;

const PRACTICE_PAGES: Walk = [
  ["/today", TODAY_TEXT.title],
  ["/insights", INSIGHTS_TEXT.title],
  ["/settings/setup", SETUP_TEXT.title],
  ["/settings/team", TEAM_TEXT.title],
  ["/settings/plan", PLAN_TEXT.title],
  ["/settings/security", SECURITY_TEXT.title],
  ["/account", SECURITY_TEXT.accountTitle],
  ["/help", HELP_TEXT.title],
];

const HQ_PAGES: Walk = [
  ["/hq", HQ_TEXT.overview.title],
  ["/hq/practices", HQ_TEXT.practices.title],
  ["/hq/organizations", HQ_TEXT.organizations.title],
  ["/hq/activity", HQ_TEXT.activity.title],
  ["/hq/spend", HQ_TEXT.spend.title],
  ["/hq/team", HQ_TEXT.team.title],
  ["/hq/demos", HQ_TEXT.demos.title],
];

function title(page: Page, name: string) {
  return page.getByRole("heading", { level: 1, name, exact: true });
}

async function walk(page: Page, origin: string, credentials: Credentials, pages: Walk, check?: PageCheck): Promise<void> {
  const problems = await keepReadOnly(page);
  await signIn(page, credentials, origin);
  await expect(title(page, pages[0]?.[1] ?? "")).toBeVisible();
  for (const [path, heading] of pages) {
    await test.step(path, async () => {
      await page.goto(`${origin}${path}`);
      await expect(title(page, heading)).toBeVisible();
      await check?.(page);
    });
  }
  expect(problems).toEqual({ refused: [], failed: [] });
}

export async function expectReady(request: APIRequestContext, origins: readonly string[]): Promise<void> {
  for (const origin of origins) {
    const response = await request.get(`${origin}/api/health/ready`);
    expect(response.status(), `${origin}/api/health/ready`).toBe(200);
    expect((await response.json()).status).toBe("ready");
  }
}

export async function walkPractice(page: Page, origin: string, credentials: Credentials, check?: PageCheck): Promise<void> {
  await walk(page, origin, credentials, PRACTICE_PAGES, check);
}

export async function walkHq(page: Page, origin: string, credentials: Credentials, check?: PageCheck): Promise<void> {
  await walk(page, origin, credentials, HQ_PAGES, check);
}
