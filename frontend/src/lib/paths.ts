export const ACCOUNT_PATH = "/account";
export const SETUP_PATH = "/settings/setup";
export const TEAM_PATH = "/settings/team";
export const SECURITY_SETTINGS_PATH = "/settings/security";
export const ACCESS_LOG_PATH = "/insights/access-log";
export const COMPLIANCE_PATH = "/compliance";
export const HISTORY_OPEN = "1";
export const ORGANIZATIONS_PATH = "/organizations";

export type OrganizationTab = "insights" | "plan" | "domains";

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
