import { expect, test, type Page } from "@playwright/test";
import { DOMAIN_TEXT } from "../../src/components/shared/domain-claims/strings";
import { PRACTICE_TEXT } from "../../src/components/shared/practices/strings";
import { SHARED_TEXT } from "../../src/components/shared/strings";
import { ORGANIZATION_TEXT } from "../../src/features/organization/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { ROLE_LABELS } from "../../src/lib/labels";
import { expectAccessible } from "../support/accessibility";
import { heading } from "../support/app";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface OrganizationDay {
  admin: Account;
  practices: [string, string];
  organization: { id: string; name: string };
  domain: string;
}

async function openTab(page: Page, organization: string, tab: string, title: string): Promise<void> {
  await page.getByRole("tablist", { name: organization }).getByRole("tab", { name: tab }).click();
  await expect(heading(page, title)).toBeVisible();
  await expectAccessible(page);
}

test("an admin of two practices switches between them and runs the organization area", async ({ page }) => {
  const day = await seed<OrganizationDay>("organization-day");
  const [north, south] = day.practices;
  const organization = day.organization.name;

  await signIn(page, day.admin);
  await expect(heading(page, TODAY_TEXT.title)).toBeVisible();
  const switcher = page.getByRole("button", { name: SHARED_TEXT.practiceSwitcher.label(north) });
  await expect(switcher).toBeVisible();
  await switcher.click();
  await page.getByRole("menuitemradio", { name: south, exact: true }).click();
  await expect(page.getByRole("button", { name: SHARED_TEXT.practiceSwitcher.label(south) })).toBeVisible();
  await expect(heading(page, TODAY_TEXT.title)).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: SHARED_TEXT.account.menu(day.admin.name, ROLE_LABELS.admin) }).click();
  await page.getByRole("menuitem", { name: PRACTICE_TEXT.organization(organization) }).click();
  await expect(page).toHaveURL(new RegExp(`/organizations/${day.organization.id}`));
  await expect(heading(page, organization)).toBeVisible();
  const practices = page.getByRole("table", { name: ORGANIZATION_TEXT.practices.tableLabel });
  await expect(practices).toContainText(north);
  await expect(practices).toContainText(south);
  await expectAccessible(page);

  await openTab(page, organization, ORGANIZATION_TEXT.tabs.plan, ORGANIZATION_TEXT.plan.title);
  await expect(page.getByRole("region", { name: ORGANIZATION_TEXT.plan.summaryLabel })).toBeVisible();

  await openTab(page, organization, ORGANIZATION_TEXT.tabs.domains, ORGANIZATION_TEXT.domains.title);
  const domains = page.getByRole("region", { name: DOMAIN_TEXT.title });
  await domains.getByRole("textbox", { name: DOMAIN_TEXT.domain }).fill(day.domain);
  await domains.getByRole("button", { name: DOMAIN_TEXT.claim, exact: true }).click();
  const claimed = page.getByRole("list", { name: DOMAIN_TEXT.listLabel }).getByRole("listitem").filter({ hasText: day.domain });
  await expect(claimed).toContainText(DOMAIN_TEXT.unverified);
  await expectAccessible(page);
});
