import type { Locator, Page } from "@playwright/test";
import { SHARED_TEXT } from "../../src/components/shared/strings";
import { organizationHref } from "../../src/features/hq/organization/organizationTabs";
import { practiceHref } from "../../src/features/hq/practice/practiceTabs";
import { HQ_TEXT } from "../../src/features/hq/strings";
import { expectAccessible } from "../support/accessibility";
import { checkDialog, type DialogCase } from "./dialogs";
import { expect, test } from "./fixtures";

const words = HQ_TEXT.practices;

function button(name: string) {
  return (page: Page) => page.getByRole("button", { name, exact: true }).first();
}

async function openPlanChoices(page: Page, renewal: Locator): Promise<void> {
  await renewal.getByRole("combobox", { name: words.renewal.plan, exact: true }).click();
  const choices = renewal.getByRole("listbox");
  await expect(choices).toBeVisible();
  await expectAccessible(page);
  await page.keyboard.press("Escape");
  await expect(choices).toBeHidden();
  await expect(renewal).toBeVisible();
}

const CASES: readonly DialogCase[] = [
  {
    name: "renew a practice, with its plan dropdown open",
    who: "hq",
    path: (world) => practiceHref(world.practice.id),
    trigger: button(HQ_TEXT.practice.renew),
    dialog: (page, world) => page.getByRole("dialog", { name: words.renewal.title(world.practice.name), exact: true }),
    inside: openPlanChoices,
  },
  {
    name: "edit a practice",
    who: "hq",
    path: (world) => practiceHref(world.practice.id),
    trigger: button(HQ_TEXT.practice.edit),
    dialog: (page, world) => page.getByRole("dialog", { name: words.form.editTitle(world.practice.name), exact: true }),
  },
  {
    name: "add an admin to a practice",
    who: "hq",
    path: (world) => practiceHref(world.practice.id),
    trigger: button(HQ_TEXT.practice.addAdmin),
    dialog: (page, world) => page.getByRole("dialog", { name: words.appoint.title(world.practice.name), exact: true }),
  },
  {
    name: "add a practice",
    who: "hq",
    path: () => "/hq/practices",
    trigger: button(words.add),
    dialog: (page) => page.getByRole("dialog", { name: words.form.addTitle, exact: true }),
  },
  {
    name: "add an organization",
    who: "hq",
    path: () => "/hq/organizations",
    trigger: button(HQ_TEXT.organizations.add),
    dialog: (page) => page.getByRole("dialog", { name: HQ_TEXT.organizations.form.addTitle, exact: true }),
  },
  {
    name: "renew an organization",
    who: "hq",
    path: (world) => organizationHref(world.organization.id),
    trigger: button(HQ_TEXT.organization.renew),
    dialog: (page, world) => page.getByRole("dialog", { name: words.renewal.title(world.organization.name), exact: true }),
  },
  {
    name: "invite to HQ",
    who: "hq",
    path: () => "/hq/team",
    trigger: button(HQ_TEXT.team.invite),
    dialog: (page) => page.getByRole("dialog", { name: HQ_TEXT.team.inviteTitle, exact: true }),
  },
  {
    name: "search the platform",
    who: "hq",
    path: () => "/hq",
    trigger: button(SHARED_TEXT.nav.search),
    dialog: (page) => page.getByRole("dialog", { name: HQ_TEXT.search.title, exact: true }),
  },
];

for (const shown of CASES) {
  test(`HQ dialog: ${shown.name}`, async ({ page, signIn }) => {
    await signIn(shown.who);
    await checkDialog(page, shown);
  });
}
