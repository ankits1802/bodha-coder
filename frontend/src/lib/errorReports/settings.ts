export interface ReportSettings {
  dsn: string;
  release: string;
  environment: string;
}

export type ReportEnvironment = Readonly<Record<string, string | undefined>>;

export const REPORT_ATTRIBUTE = "data-error-reports";

const SENTRY_DSN = /^https:\/\/[0-9a-f]+@[a-z0-9.-]+(?::\d+)?\/\d+$/;
const UNVERSIONED = "unversioned";
const DEFAULT_ENVIRONMENT = "production";

export function reportSettingsFrom(environment: ReportEnvironment): ReportSettings | null {
  const dsn = environment.WEB_SENTRY_DSN?.trim() ?? "";
  if (!dsn) return null;
  if (!SENTRY_DSN.test(dsn)) throw new Error("WEB_SENTRY_DSN must be the https DSN of a Sentry project");
  return {
    dsn,
    release: environment.APP_VERSION?.trim() || UNVERSIONED,
    environment: environment.APP_ENVIRONMENT?.trim() || DEFAULT_ENVIRONMENT,
  };
}

export function ingestOrigin(dsn: string): string {
  return new URL(dsn).origin;
}

export function encodeSettings(settings: ReportSettings | null): string | undefined {
  return settings ? JSON.stringify(settings) : undefined;
}

export function decodeSettings(text: string | null): ReportSettings | null {
  if (!text) return null;
  try {
    const parsed: unknown = JSON.parse(text);
    if (typeof parsed !== "object" || parsed === null) return null;
    const { dsn, release, environment } = parsed as Record<string, unknown>;
    if (typeof dsn !== "string" || !SENTRY_DSN.test(dsn) || typeof release !== "string" || typeof environment !== "string") return null;
    return { dsn, release, environment };
  } catch {
    return null;
  }
}
