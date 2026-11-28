export const ORGANIZATION_TABS = ["practices", "admins", "plan", "spend"] as const;
export type OrganizationTab = (typeof ORGANIZATION_TABS)[number];

const DEFAULT_TAB: OrganizationTab = "practices";
export const ORGANIZATIONS_LIST_PATH = "/hq/organizations";

function isOrganizationTab(value: string | null): value is OrganizationTab {
  return value !== null && (ORGANIZATION_TABS as readonly string[]).includes(value);
}

export function organizationTabFrom(value: string | null): OrganizationTab {
  return isOrganizationTab(value) ? value : DEFAULT_TAB;
}

export function organizationHref(organizationId: string, tab?: OrganizationTab): string {
  const path = `${ORGANIZATIONS_LIST_PATH}/${encodeURIComponent(organizationId)}`;
  return tab ? `${path}?tab=${tab}` : path;
}
