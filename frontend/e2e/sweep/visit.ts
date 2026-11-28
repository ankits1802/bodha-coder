import { expect, type Locator, type Page } from "@playwright/test";
import { SHARED_TEXT } from "../../src/components/shared/strings";
import { expectAccessible } from "../support/accessibility";
import { expectReachedByTab } from "../support/keyboard";

const BUSY = "[aria-busy='true'], .animate-spin, .animate-pulse";
const PRIMARY = "button.bg-primary:not([disabled]), a.bg-primary";
const FIRST_SERVER_ERROR = 500;

export interface Screen {
  path: string;
  lands?: string;
  ready?: (page: Page) => Locator;
}

export async function settle(page: Page, ready?: Locator): Promise<void> {
  await expect(ready ?? page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await expect(page.locator(BUSY)).toHaveCount(0);
}

export function primaryAction(scope: Page | Locator): Locator {
  return scope.locator(PRIMARY).filter({ visible: true }).first();
}

export async function expectPrimaryByKeyboard(page: Page): Promise<void> {
  const primary = primaryAction(page);
  if ((await primary.count()) === 0) return;
  await expectReachedByTab(page, primary);
}

export async function open(page: Page, origin: string, screen: Screen): Promise<void> {
  const failures: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= FIRST_SERVER_ERROR) failures.push(`${response.request().method()} ${response.url()} ${response.status()}`);
  });
  await page.goto(`${origin}${screen.path}`);
  await settle(page, screen.ready?.(page));
  expect(new URL(page.url()).pathname, "the page did not send this person elsewhere").toBe(
    screen.lands ?? new URL(screen.path, origin).pathname,
  );
  await expect(page.getByText(SHARED_TEXT.notAllowed)).toHaveCount(0);
  expect(failures, "no request failed on the server").toEqual([]);
}

export async function sweep(page: Page, origin: string, screen: Screen): Promise<void> {
  await open(page, origin, screen);
  await expectAccessible(page);
  await expectPrimaryByKeyboard(page);
}
