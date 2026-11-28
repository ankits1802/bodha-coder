import { organizationHref, ORGANIZATION_TABS } from "../../src/features/hq/organization/organizationTabs";
import { practiceHref, PRACTICE_TABS } from "../../src/features/hq/practice/practiceTabs";
import { ADMIN_ORIGIN } from "../support/app";
import { test } from "./fixtures";
import { HQ_ROUTES } from "./routes";
import { sweep } from "./visit";
import { sweepWorld } from "./world";

for (const path of HQ_ROUTES) {
  test(`HQ on ${path}`, async ({ page, signIn }) => {
    await signIn("hq");
    await sweep(page, ADMIN_ORIGIN, { path });
  });
}

for (const tab of PRACTICE_TABS) {
  test(`HQ on a practice, ${tab} tab`, async ({ page, signIn }) => {
    const world = await sweepWorld();
    await signIn("hq");
    await sweep(page, ADMIN_ORIGIN, { path: practiceHref(world.practice.id, tab) });
  });
}

test("HQ on a practice with no notes", async ({ page, signIn }) => {
  const world = await sweepWorld();
  await signIn("hq");
  await sweep(page, ADMIN_ORIGIN, { path: practiceHref(world.empty.id) });
});

test("HQ on a practice whose plan has ended", async ({ page, signIn }) => {
  const world = await sweepWorld();
  await signIn("hq");
  await sweep(page, ADMIN_ORIGIN, { path: practiceHref(world.lapsed.id, "plan") });
});

for (const tab of ORGANIZATION_TABS) {
  test(`HQ on an organization, ${tab} tab`, async ({ page, signIn }) => {
    const world = await sweepWorld();
    await signIn("hq");
    await sweep(page, ADMIN_ORIGIN, { path: organizationHref(world.organization.id, tab) });
  });
}
