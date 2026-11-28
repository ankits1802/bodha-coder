import { NAV_ORDER } from "../../src/features/setup/setupModel";
import { PLAN_PATH } from "../../src/lib/roles";
import { noteHistoryPath, notePath, organizationPath, setupSectionPath, type OrganizationTab } from "../../src/lib/paths";
import { expectAccessible } from "../support/accessibility";
import { SITE_ORIGIN } from "../support/app";
import { test } from "./fixtures";
import { PRACTICE_ROUTES, rolesFor } from "./routes";
import { open, sweep } from "./visit";
import { sweepWorld, type NoteKey, type Who } from "./world";

const NOTE_VISITS: readonly [Who, NoteKey][] = [
  ["admin", "ready"],
  ["admin", "coder"],
  ["admin", "provider"],
  ["admin", "asked"],
  ["admin", "compliance"],
  ["admin", "approved"],
  ["coder", "coder"],
  ["coder", "ready"],
  ["cdi", "provider"],
  ["compliance", "compliance"],
  ["biller", "approved"],
];
const ORGANIZATION_TABS: readonly (OrganizationTab | undefined)[] = [undefined, "insights", "plan", "domains", "sign-in"];
const EMPTY_SETUP_SECTIONS = ["providers", "payers", "intake"] as const;

for (const route of PRACTICE_ROUTES) {
  for (const who of rolesFor(route.area)) {
    test(`${who} on ${route.path} with data`, async ({ page, signIn }) => {
      await signIn(who);
      await sweep(page, SITE_ORIGIN, { path: route.path });
    });
  }
  if (!rolesFor(route.area).includes("admin")) continue;
  test(`admin on ${route.path} of an empty practice`, async ({ page, signIn }) => {
    await signIn("empty_admin");
    await sweep(page, SITE_ORIGIN, { path: route.path });
  });
}

for (const section of NAV_ORDER) {
  test(`admin on setup section ${section}`, async ({ page, signIn }) => {
    await signIn("admin");
    await sweep(page, SITE_ORIGIN, { path: setupSectionPath(section) });
  });
}

for (const section of EMPTY_SETUP_SECTIONS) {
  test(`admin on setup section ${section} of an empty practice`, async ({ page, signIn }) => {
    await signIn("empty_admin");
    await sweep(page, SITE_ORIGIN, { path: setupSectionPath(section) });
  });
}

for (const [who, key] of NOTE_VISITS) {
  test(`${who} reviews the ${key} note`, async ({ page, signIn }) => {
    const note = (await sweepWorld()).notes[key];
    await signIn(who);
    await sweep(page, SITE_ORIGIN, {
      path: notePath(note.id),
      ready: (shown) => shown.getByRole("heading", { level: 1, name: note.patient }),
    });
  });
}

test("admin opens the history of an approved note", async ({ page, signIn }) => {
  const note = (await sweepWorld()).notes.approved;
  await signIn("admin");
  await open(page, SITE_ORIGIN, {
    path: noteHistoryPath(note.id),
    ready: (shown) => shown.getByRole("dialog").getByRole("heading", { level: 2 }),
  });
  await expectAccessible(page);
});

for (const tab of ORGANIZATION_TABS) {
  test(`organization admin on the organization ${tab ?? "practices"} tab`, async ({ page, signIn }) => {
    const world = await sweepWorld();
    await signIn("admin");
    await sweep(page, SITE_ORIGIN, { path: organizationPath(world.organization.id, tab) });
  });
}

test("coder on a blind audit sample", async ({ page, signIn }) => {
  const world = await sweepWorld();
  await signIn("coder");
  await sweep(page, SITE_ORIGIN, { path: `/insights/quality/review/${world.samples.audit}` });
});

test("coder on a training set", async ({ page, signIn }) => {
  const world = await sweepWorld();
  await signIn("coder");
  await sweep(page, SITE_ORIGIN, { path: `/training/${world.samples.training}` });
});

test("billing-only admin on the plan", async ({ page, signIn }) => {
  await signIn("lapsed_admin");
  await sweep(page, SITE_ORIGIN, { path: PLAN_PATH });
});

test("billing-only admin is sent from today to the plan", async ({ page, signIn }) => {
  await signIn("lapsed_admin");
  await sweep(page, SITE_ORIGIN, { path: "/today", lands: PLAN_PATH });
});
