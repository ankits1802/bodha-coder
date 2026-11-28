import { test } from "@playwright/test";
import { setting } from "./readOnly";
import { expectReady, walkHq, walkPractice } from "./walks";

const SITE_URL = process.env.CANARY_SITE_URL || "https://www.bodhaai.co";
const ADMIN_URL = process.env.CANARY_ADMIN_URL || "https://admin.bodhaai.co";

test("the API answers ready on both hosts", async ({ request }) => {
  await expectReady(request, [SITE_URL, ADMIN_URL]);
});

test("the practice canary signs in and opens the practice pages", async ({ page }) => {
  await walkPractice(page, SITE_URL, {
    email: setting("CANARY_PRACTICE_EMAIL"),
    password: setting("CANARY_PRACTICE_PASSWORD"),
    two_step_secret: setting("CANARY_PRACTICE_TOTP_SECRET"),
  });
});

test("the HQ canary signs in on the admin host and opens the HQ pages", async ({ page }) => {
  await walkHq(page, ADMIN_URL, {
    email: setting("CANARY_HQ_EMAIL"),
    password: setting("CANARY_HQ_PASSWORD"),
    two_step_secret: setting("CANARY_HQ_TOTP_SECRET"),
  });
});
