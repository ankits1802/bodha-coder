import type { Page } from "@playwright/test";
import type { Appearance } from "../../src/lib/api/types";
import { SITE_ORIGIN } from "../support/app";
import { expect, test } from "./fixtures";
import { open } from "./visit";

const PAGE_BACKGROUND = { light: "rgb(250, 250, 248)", dark: "rgb(17, 17, 19)" } as const;
const BODY_SIZE = { default: "14px", large: "15.75px", larger: "17.5px" } as const;

function themeOf(appearance: Appearance | null, systemDark: boolean): keyof typeof PAGE_BACKGROUND {
  if (appearance?.theme === "dark") return "dark";
  if (appearance?.theme === "light") return "light";
  return systemDark ? "dark" : "light";
}

async function expectLook(page: Page, appearance: Appearance | null): Promise<void> {
  const body = page.locator("body");
  const systemDark = test.info().project.use.colorScheme === "dark";
  await expect(body).toHaveCSS("background-color", PAGE_BACKGROUND[themeOf(appearance, systemDark)]);
  await expect(body).toHaveCSS("font-size", BODY_SIZE[appearance?.text_size ?? "default"]);
}

test("public pages follow the system and this device's appearance", async ({ page, appearance }) => {
  await open(page, SITE_ORIGIN, { path: "/sign-in" });
  await expectLook(page, appearance);
});

test("the app follows the person's appearance", async ({ page, appearance, signIn }) => {
  await signIn("coder");
  await open(page, SITE_ORIGIN, { path: "/account" });
  await expectLook(page, appearance);
});
