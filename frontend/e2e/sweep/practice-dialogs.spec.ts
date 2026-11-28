import { SIGNATURE_TEXT } from "../../src/components/shared/signature/strings";
import { SSO_TEXT } from "../../src/components/shared/single-sign-on/strings";
import { SHARED_TEXT } from "../../src/components/shared/strings";
import { INVITE_ROWS_TEXT } from "../../src/components/shared/team-invite/strings";
import { COMPLIANCE_TEXT } from "../../src/features/compliance/strings";
import { REVIEW_TEXT } from "../../src/features/note-review/strings";
import { ORGANIZATION_TEXT } from "../../src/features/organization/strings";
import { QUEUE_TEXT } from "../../src/features/queue/strings";
import { SEARCH_TEXT } from "../../src/features/search/strings";
import { MIPS_TEXT, PAYER_TEXT, PRACTICE_MEASURE_TEXT, PROVIDER_TEXT } from "../../src/features/setup/strings";
import { TEAM_TEXT } from "../../src/features/team/strings";
import { notePath, organizationPath, SECURITY_SETTINGS_PATH, setupSectionPath, TEAM_PATH } from "../../src/lib/paths";
import type { Page } from "@playwright/test";
import { expectAccessible } from "../support/accessibility";
import { SITE_ORIGIN } from "../support/app";
import { checkDialog, startingWith, type DialogCase } from "./dialogs";
import { expect, test } from "./fixtures";
import { open } from "./visit";
import { sweepWorld, type NoteKey, type SweepWorld } from "./world";

function button(name: string | RegExp) {
  return (page: Page) => page.getByRole("button", { name, exact: typeof name === "string" });
}

function dialog(name: string | RegExp) {
  return (page: Page) => page.getByRole("dialog", { name, exact: typeof name === "string" });
}

function onNote(key: NoteKey) {
  return {
    path: (world: SweepWorld) => notePath(world.notes[key].id),
    ready: (page: Page, world: SweepWorld) => page.getByRole("heading", { level: 1, name: world.notes[key].patient }),
  };
}

const CASES: readonly DialogCase[] = [
  { name: "invite the team", who: "admin", path: () => TEAM_PATH, trigger: button(TEAM_TEXT.invite), dialog: dialog(INVITE_ROWS_TEXT.title) },
  {
    name: "add a provider",
    who: "admin",
    path: () => setupSectionPath("providers"),
    trigger: button(PROVIDER_TEXT.add),
    dialog: dialog(PROVIDER_TEXT.dialog.addTitle),
  },
  {
    name: "add a payer",
    who: "admin",
    path: () => setupSectionPath("payers"),
    trigger: (page) => page.getByRole("region", { name: PAYER_TEXT.title }).getByRole("button", { name: PAYER_TEXT.add, exact: true }),
    dialog: dialog(PAYER_TEXT.dialog.addTitle),
  },
  {
    name: "the practice measure editor",
    who: "admin",
    path: () => setupSectionPath("mips"),
    before: (page) => page.getByRole("radiogroup", { name: MIPS_TEXT.modeLabel }).getByRole("radio", { name: MIPS_TEXT.custom }).click(),
    trigger: button(PRACTICE_MEASURE_TEXT.add),
    dialog: dialog(PRACTICE_MEASURE_TEXT.dialog.addTitle),
  },
  {
    name: "turn off single sign-on",
    who: "admin",
    path: () => SECURITY_SETTINGS_PATH,
    trigger: button(SSO_TEXT.removeAll),
    dialog: dialog(SSO_TEXT.removeTitle),
  },
  {
    name: "ask the provider",
    who: "cdi",
    ...onNote("provider"),
    trigger: (page, world) => page.getByRole("button", { name: startingWith(`${REVIEW_TEXT.askDialog.title(world.provider.name)} `) }),
    dialog: (page, world) => page.getByRole("dialog", { name: REVIEW_TEXT.askDialog.title(world.provider.name), exact: true }),
  },
  {
    name: "adopt a signature to approve",
    who: "coder",
    ...onNote("ready"),
    trigger: (page) => page.getByRole("button", { name: startingWith(REVIEW_TEXT.actions.approve) }).first(),
    dialog: dialog(SIGNATURE_TEXT.addTitle),
  },
  { name: "adopt a signature from the account", who: "coder", path: () => "/account", trigger: button(SIGNATURE_TEXT.add), dialog: dialog(SIGNATURE_TEXT.addTitle) },
  { name: "flag a note", who: "coder", ...onNote("coder"), trigger: button(REVIEW_TEXT.actions.flag), dialog: dialog(REVIEW_TEXT.flagDialog.title) },
  {
    name: "return a note to the coder from the review",
    who: "compliance",
    ...onNote("compliance"),
    trigger: button(REVIEW_TEXT.actions.returnToCoder),
    dialog: dialog(SHARED_TEXT.returnDialog.title),
  },
  {
    name: "return a case to the coder",
    who: "compliance",
    path: () => "/compliance",
    trigger: (page, world) =>
      page.getByRole("article", { name: world.notes.compliance.patient }).getByRole("button", { name: COMPLIANCE_TEXT.returnToCoder, exact: true }),
    dialog: dialog(SHARED_TEXT.returnDialog.title),
  },
  { name: "save a queue view", who: "coder", path: () => "/queue", trigger: button(QUEUE_TEXT.views.save), dialog: dialog(QUEUE_TEXT.views.saveTitle) },
  { name: "search notes", who: "coder", path: () => "/queue", trigger: button(SHARED_TEXT.nav.search), dialog: dialog(SEARCH_TEXT.title) },
  {
    name: "add a practice to the organization",
    who: "admin",
    path: (world) => organizationPath(world.organization.id),
    trigger: button(ORGANIZATION_TEXT.practices.newPractice),
    dialog: dialog(ORGANIZATION_TEXT.location.title),
  },
  {
    name: "add a person to the organization",
    who: "admin",
    path: (world) => organizationPath(world.organization.id),
    trigger: button(ORGANIZATION_TEXT.practices.addPerson),
    dialog: dialog(ORGANIZATION_TEXT.person.title),
  },
];

for (const shown of CASES) {
  test(`dialog: ${shown.name}`, async ({ page, signIn }) => {
    await signIn(shown.who);
    await checkDialog(page, shown);
  });
}

test("the override reason a coder gives by keyboard", async ({ page, signIn }) => {
  const world = await sweepWorld();
  const note = world.notes.coder;
  await signIn("coder");
  await open(page, SITE_ORIGIN, { path: notePath(note.id), ready: (shown) => shown.getByRole("heading", { level: 1, name: note.patient }) });
  await page.keyboard.press("n");
  await expect(page.getByRole("group", { name: startingWith(REVIEW_TEXT.override.label("")) })).toBeVisible();
  await expectAccessible(page);
});

test("the keyboard shortcuts", async ({ page, signIn }) => {
  await signIn("coder");
  await open(page, SITE_ORIGIN, { path: "/queue" });
  await page.keyboard.press("?");
  const shortcuts = page.getByRole("dialog", { name: SHARED_TEXT.shortcuts.title, exact: true });
  await expect(shortcuts).toBeVisible();
  await expectAccessible(page);
  await page.keyboard.press("Escape");
  await expect(shortcuts).toBeHidden();
});
