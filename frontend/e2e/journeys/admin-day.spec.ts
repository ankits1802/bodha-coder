import { expect, test, type Page } from "@playwright/test";
import { SHARED_TEXT } from "../../src/components/shared/strings";
import { INVITE_ROWS_TEXT } from "../../src/components/shared/team-invite/strings";
import { PLAN_TEXT } from "../../src/features/plan/strings";
import { SECURITY_TEXT } from "../../src/features/security/strings";
import { PAYER_TEXT, PROVIDER_TEXT, SETUP_TEXT } from "../../src/features/setup/strings";
import { TEAM_TEXT } from "../../src/features/team/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { ROLE_LABELS } from "../../src/lib/labels";
import { expectAccessible } from "../support/accessibility";
import { EMAIL_DOMAIN, heading, marker } from "../support/app";
import { nextMessage } from "../support/mailbox";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface AdminDay {
  admin: Account;
  practice: string;
}

const words = TODAY_TEXT.checklist;

function optional(label: string): string {
  return `${label}, ${PROVIDER_TEXT.dialog.optional}`;
}

async function openTab(page: Page, tab: string, title: string): Promise<void> {
  await page.getByRole("tablist", { name: SHARED_TEXT.nav.settings }).getByRole("tab", { name: tab }).click();
  await expect(heading(page, title)).toBeVisible();
  await expectAccessible(page);
}

async function stepDone(page: Page, step: string): Promise<void> {
  const row = page.getByRole("region", { name: words.title }).getByRole("listitem").filter({ hasText: step });
  await expect(row).toHaveText(new RegExp(`^${words.done}${step}`));
}

test("an admin works through the first day: provider, payer, invite, role and settings", async ({ page }) => {
  const { admin, practice } = await seed<AdminDay>("admin-day");
  const run = marker();
  const coder = { name: "Jordan Newcoder", email: `new-coder-${run}@${EMAIL_DOMAIN}` };

  await signIn(page, admin);
  await expect(heading(page, TODAY_TEXT.title)).toBeVisible();
  const checklist = page.getByRole("region", { name: words.title });
  await expect(checklist).toBeVisible();
  await expectAccessible(page);

  await checklist.getByRole("link", { name: words.actions.addProvider }).click();
  const providerDialog = page.getByRole("dialog", { name: PROVIDER_TEXT.dialog.addTitle });
  await expect(providerDialog).toBeVisible();
  await expectAccessible(page);
  await providerDialog.getByLabel(PROVIDER_TEXT.dialog.name, { exact: true }).fill("Priya Raman");
  await providerDialog.getByLabel(optional(PROVIDER_TEXT.dialog.npi), { exact: true }).fill("1456789019");
  await providerDialog.getByLabel(PROVIDER_TEXT.dialog.email, { exact: true }).fill(`dr-raman-${run}@${EMAIL_DOMAIN}`);
  await providerDialog.getByRole("button", { name: PROVIDER_TEXT.dialog.save }).click();
  await expect(providerDialog).toBeHidden();
  await expect(page.getByRole("table", { name: PROVIDER_TEXT.tableLabel })).toContainText("Priya Raman");

  await page.goto("/settings/setup?section=payers");
  await page.getByRole("region", { name: PAYER_TEXT.title }).getByRole("button", { name: PAYER_TEXT.add }).click();
  const payerDialog = page.getByRole("dialog", { name: PAYER_TEXT.dialog.addTitle });
  await payerDialog.getByLabel(PAYER_TEXT.dialog.name, { exact: true }).fill("Synthetic Health Plan");
  await payerDialog.getByLabel(optional(PAYER_TEXT.dialog.payerId), { exact: true }).fill("SYN01");
  await payerDialog.getByRole("combobox", { name: PAYER_TEXT.dialog.planType }).click();
  await page.getByRole("option", { name: PAYER_TEXT.planTypes.medicare, exact: true }).click();
  await payerDialog.getByRole("button", { name: PAYER_TEXT.dialog.save }).click();
  await expect(payerDialog).toBeHidden();
  await expect(page.getByRole("table", { name: PAYER_TEXT.tableLabel })).toContainText("Synthetic Health Plan");
  await expectAccessible(page);

  await openTab(page, SHARED_TEXT.tabs.team, TEAM_TEXT.title);
  await page.getByRole("button", { name: TEAM_TEXT.invite, exact: true }).click();
  const invite = page.getByRole("dialog", { name: INVITE_ROWS_TEXT.title });
  await invite.getByLabel(INVITE_ROWS_TEXT.nameFor(1), { exact: true }).fill(coder.name);
  await invite.getByLabel(INVITE_ROWS_TEXT.emailFor(1), { exact: true }).fill(coder.email);
  await invite.getByRole("button", { name: INVITE_ROWS_TEXT.send(1) }).click();
  await expect(page.getByRole("status").filter({ hasText: INVITE_ROWS_TEXT.sent(1) })).toBeVisible();
  await nextMessage(coder.email, (message) => message.subject === `Join ${practice} on Bodha Assure`);

  await page.getByRole("combobox", { name: TEAM_TEXT.roleFor(coder.name) }).click();
  await page.getByRole("option", { name: ROLE_LABELS.biller, exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: TEAM_TEXT.roleChanged(coder.name) })).toBeVisible();
  await expect(page.getByRole("combobox", { name: TEAM_TEXT.roleFor(coder.name) })).toContainText(ROLE_LABELS.biller);

  await openTab(page, SHARED_TEXT.tabs.plan, PLAN_TEXT.title);
  await openTab(page, SHARED_TEXT.tabs.security, SECURITY_TEXT.title);
  await openTab(page, SHARED_TEXT.tabs.setup, SETUP_TEXT.title);

  await page.goto("/today");
  await stepDone(page, words.steps.providers);
  await stepDone(page, words.steps.payers);
  await stepDone(page, words.steps.invite);
});
