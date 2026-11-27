export const ACCOUNT_PATH = "/account";
export const SETUP_PATH = "/settings/setup";
export const TEAM_PATH = "/settings/team";
export const SECURITY_SETTINGS_PATH = "/settings/security";

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

export function accessLogPath(userId: string): string {
  return `${SECURITY_SETTINGS_PATH}?${new URLSearchParams({ user: userId }).toString()}`;
}
