import { expect, type Locator, type Page } from "@playwright/test";

const MAX_TAB_STOPS = 300;
const MAX_TRAP_STOPS = 40;
const EXTRA_TRAP_STOPS = 2;
const TABBABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type=hidden])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

async function look(target: Locator): Promise<string[]> {
  return target.evaluate((element) => {
    const style = getComputedStyle(element);
    const drawn = style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0;
    const outline = drawn ? `${style.outlineStyle} ${style.outlineWidth} ${style.outlineColor}` : "none";
    return [outline, style.boxShadow, style.borderColor, style.backgroundColor];
  });
}

function isFocused(target: Locator): Promise<boolean> {
  return target.evaluate((element) => element === document.activeElement);
}

export async function expectReachedByTab(page: Page, target: Locator): Promise<void> {
  await target.evaluate((element) => {
    if (element === document.activeElement && element instanceof HTMLElement) element.blur();
  });
  const resting = await look(target);
  for (let stop = 0; stop < MAX_TAB_STOPS; stop += 1) {
    await page.keyboard.press("Tab");
    if (!(await isFocused(target))) continue;
    const focused = await look(target);
    const shown = focused[0] !== "none" || focused.some((value, index) => value !== resting[index]);
    expect(shown, `${target} shows where focus is`).toBe(true);
    return;
  }
  throw new Error(`Tab did not reach ${target} within ${MAX_TAB_STOPS} stops`);
}

export async function openByKeyboard(page: Page, trigger: Locator, dialog: Locator): Promise<void> {
  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(dialog).toBeVisible();
}

async function focusStaysIn(dialog: Locator): Promise<boolean> {
  return dialog.evaluate((element) => {
    const active = document.activeElement;
    return active === null || active === document.body || element.contains(active);
  });
}

export async function expectFocusTrapped(page: Page, dialog: Locator): Promise<void> {
  const stops = await dialog.evaluate((element, selector) => element.querySelectorAll(selector).length, TABBABLE);
  const presses = Math.min(stops + EXTRA_TRAP_STOPS, MAX_TRAP_STOPS);
  expect(await focusStaysIn(dialog), "focus moves into the dialog when it opens").toBe(true);
  for (const key of ["Tab", "Shift+Tab"]) {
    for (let press = 0; press < presses; press += 1) {
      await page.keyboard.press(key);
      expect(await focusStaysIn(dialog), `focus stays in the dialog after ${press + 1} × ${key}`).toBe(true);
    }
  }
}

export async function expectFocusReturned(page: Page, dialog: Locator, trigger: Locator): Promise<void> {
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger, "focus returns to what opened the dialog").toBeFocused();
}

export async function expectStill(page: Page): Promise<void> {
  const moving = await page.evaluate(() =>
    document
      .getAnimations()
      .filter((animation) => animation.playState === "running" && animation.effect?.getComputedTiming().iterations === Infinity)
      .map((animation) => {
        const target = animation.effect instanceof KeyframeEffect ? animation.effect.target : null;
        const name = animation instanceof CSSAnimation ? animation.animationName : "animation";
        return `${name} on <${target?.tagName.toLowerCase() ?? "?"} class="${target?.getAttribute("class") ?? ""}">`;
      }),
  );
  expect(moving, "nothing loops when reduced motion is asked for").toEqual([]);
}
