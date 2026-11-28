import { test } from "@playwright/test";
import { expectReady, walkHq, walkPractice } from "../canary/walks";
import { expectAccessible } from "../support/accessibility";
import { ADMIN_ORIGIN, SITE_ORIGIN } from "../support/app";
import { seed, type Account } from "../support/seed";

interface CanaryDay {
  practice: Account;
  hq: Account;
}

test("the nightly canary's read-only walk passes against this stack", async ({ page, browser, request }) => {
  const day = await seed<CanaryDay>("canary-day");
  await expectReady(request, [SITE_ORIGIN, ADMIN_ORIGIN]);
  await walkPractice(page, SITE_ORIGIN, day.practice, expectAccessible);
  const hq = await browser.newPage();
  await walkHq(hq, ADMIN_ORIGIN, day.hq, expectAccessible);
  await hq.context().close();
});
