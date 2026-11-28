import type { Page } from "@playwright/test";
import { notePath } from "../../src/lib/paths";
import { expectStill } from "../support/keyboard";
import { SITE_ORIGIN } from "../support/app";
import { expect, test } from "./fixtures";
import { sweep, type Screen } from "./visit";
import { sweepWorld, type NoteKey, type Who } from "./world";

interface Look {
  name: string;
  who: Who | null;
  path: string;
  note?: NoteKey;
}

const PHONE = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true };

const PHONE_LOOKS: readonly Look[] = [
  { name: "landing", who: null, path: "/" },
  { name: "sign-in", who: null, path: "/sign-in" },
  { name: "today", who: "admin", path: "/today" },
  { name: "queue", who: "coder", path: "/queue" },
  { name: "note review", who: "coder", path: "", note: "coder" },
  { name: "compliance", who: "compliance", path: "/compliance" },
  { name: "billing", who: "biller", path: "/billing" },
  { name: "team", who: "admin", path: "/settings/team" },
];

const STILL_LOOKS: readonly Look[] = [
  { name: "landing", who: null, path: "/" },
  { name: "pricing", who: null, path: "/pricing" },
  { name: "today", who: "admin", path: "/today" },
  { name: "note review", who: "coder", path: "", note: "coder" },
  { name: "insights", who: "admin", path: "/insights" },
];

async function screenFor(look: Look): Promise<Screen> {
  if (!look.note) return { path: look.path };
  const note = (await sweepWorld()).notes[look.note];
  return { path: notePath(note.id), ready: (page: Page) => page.getByRole("heading", { level: 1, name: note.patient }) };
}

async function expectNoSidewaysScroll(page: Page): Promise<void> {
  const sticking = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    if (document.documentElement.scrollWidth <= width) return [];
    const clipped = (element: Element) => {
      for (let parent = element.parentElement; parent; parent = parent.parentElement) {
        if (getComputedStyle(parent).overflowX !== "visible") return parent !== document.body && parent !== document.documentElement;
      }
      return false;
    };
    const wide = [...document.querySelectorAll("body *")].filter((element) => element.getBoundingClientRect().right > width + 1 && !clipped(element));
    const outermost = wide
      .filter((element) => !wide.includes(element.parentElement as Element))
      .map((element) => `<${element.tagName.toLowerCase()} class="${element.getAttribute("class") ?? ""}"> ends at ${Math.round(element.getBoundingClientRect().right)}px`);
    return outermost.length > 0 ? outermost : [`the page is ${document.documentElement.scrollWidth}px wide`];
  });
  expect(sticking, `the page fits the phone's width of ${PHONE.viewport.width}px`).toEqual([]);
}

test.describe("phone width", () => {
  test.use(PHONE);
  for (const look of PHONE_LOOKS) {
    test(`${look.name} on a phone`, async ({ page, signIn }) => {
      if (look.who) await signIn(look.who);
      await sweep(page, SITE_ORIGIN, await screenFor(look));
      await expectNoSidewaysScroll(page);
    });
  }
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });
  for (const look of STILL_LOOKS) {
    test(`${look.name} with reduced motion`, async ({ page, signIn }) => {
      if (look.who) await signIn(look.who);
      await sweep(page, SITE_ORIGIN, await screenFor(look));
      await expectStill(page);
    });
  }
});
