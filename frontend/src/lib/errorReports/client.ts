import { BROWSER_INTEGRATIONS, keptIntegrations, reportOptions } from "./options";
import { decodeSettings, REPORT_ATTRIBUTE, type ReportSettings } from "./settings";

export function settingsInPage(): ReportSettings | null {
  if (typeof document === "undefined") return null;
  return decodeSettings(document.documentElement.getAttribute(REPORT_ATTRIBUTE));
}

export async function startBrowserReports(): Promise<boolean> {
  const settings = settingsInPage();
  if (!settings) return false;
  const Sentry = await import("@sentry/nextjs");
  Sentry.init({ ...reportOptions(settings), integrations: keptIntegrations(BROWSER_INTEGRATIONS) });
  return true;
}

export function reportError(error: unknown): void {
  if (!settingsInPage()) return;
  void import("@sentry/nextjs").then((Sentry) => Sentry.captureException(error));
}
