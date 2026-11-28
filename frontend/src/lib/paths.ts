export const ACCOUNT_PATH = "/account";
export const SETUP_PATH = "/settings/setup";
export const TEAM_PATH = "/settings/team";
export const SECURITY_SETTINGS_PATH = "/settings/security";
export const ACCESS_LOG_PATH = "/insights/access-log";
export const USAGE_PATH = "/insights/usage";
export const COMPLIANCE_PATH = "/compliance";
export const BILLING_PATH = "/billing";
export const HISTORY_OPEN = "1";
export const ORGANIZATIONS_PATH = "/organizations";

export type OrganizationTab = "insights" | "plan" | "domains" | "sign-in";

export function organizationPath(organizationId: string, tab?: OrganizationTab): string {
  const base = `${ORGANIZATIONS_PATH}/${encodeURIComponent(organizationId)}`;
  return tab ? `${base}/${tab}` : base;
}

export function notePath(noteId: string): string {
  return `/notes/${encodeURIComponent(noteId)}`;
}

export function noteHistoryPath(noteId: string): string {
  return `${notePath(noteId)}?${new URLSearchParams({ history: HISTORY_OPEN }).toString()}`;
}

const SETUP_OPENS = ["addProvider", "importProviders", "addPayer"] as const;

export type SetupOpen = (typeof SETUP_OPENS)[number];

export function isSetupOpen(value: string | null): value is SetupOpen {
  return value !== null && (SETUP_OPENS as readonly string[]).includes(value);
}

export function setupSectionPath(section: string, open?: SetupOpen): string {
  const query = new URLSearchParams({ section });
  if (open) query.set("open", open);
  return `${SETUP_PATH}?${query.toString()}`;
}

export interface DayRange {
  start: string;
  end: string;
}

export function accessLogPath(userId: string, range: DayRange): string {
  return `${ACCESS_LOG_PATH}?${new URLSearchParams({ user: userId, start: range.start, end: range.end }).toString()}`;
}

const SAME_SITE_PATH = /^\/(?![/\\])[A-Za-z0-9\-._~!$&'()*+,;=:@%/?]*$/;
const NEXT_PATH_LENGTH = 512;
const NOT_A_PAGE = ["/api/", "/sign-in"];

export function sameSitePath(value: string | null | undefined): string | null {
  if (!value || value.length > NEXT_PATH_LENGTH || !SAME_SITE_PATH.test(value)) return null;
  return NOT_A_PAGE.some((prefix) => value.startsWith(prefix)) ? null : value;
}
