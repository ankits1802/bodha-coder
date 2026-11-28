import type { init } from "@sentry/nextjs";
import { scrubBreadcrumb, scrubEvent } from "./scrub";
import type { ReportSettings } from "./settings";

export type ReportOptions = NonNullable<Parameters<typeof init>[0]>;
type Integration = { name: string };

export const BROWSER_INTEGRATIONS: ReadonlySet<string> = new Set([
  "EventFilters",
  "FunctionToString",
  "BrowserApiErrors",
  "Breadcrumbs",
  "GlobalHandlers",
  "LinkedErrors",
  "Dedupe",
  "NextjsClientStackFrameNormalization",
]);

export const SERVER_INTEGRATIONS: ReadonlySet<string> = new Set([
  "EventFilters",
  "FunctionToString",
  "LinkedErrors",
  "Dedupe",
  "OnUncaughtException",
  "OnUnhandledRejection",
  "DistDirRewriteFrames",
]);

export const DATA_COLLECTION = {
  userInfo: false,
  cookies: false,
  httpHeaders: { request: false, response: false },
  httpBodies: [],
  urlQueryParams: false,
  graphQL: { document: false, variables: false },
  genAI: { inputs: false, outputs: false },
  mcp: { inputs: false, outputs: false },
  databaseQueryData: false,
  queues: false,
  stackFrameVariables: false,
  frameContextLines: 0,
};

export function keptIntegrations<T extends Integration>(allowed: ReadonlySet<string>): (defaults: T[]) => T[] {
  return (defaults) => defaults.filter((integration) => allowed.has(integration.name));
}

export function reportOptions(settings: ReportSettings) {
  return {
    dsn: settings.dsn,
    release: settings.release,
    environment: settings.environment,
    dataCollection: DATA_COLLECTION,
    sendClientReports: false,
    attachStacktrace: false,
    maxBreadcrumbs: 30,
    beforeSend: scrubEvent,
    beforeBreadcrumb: scrubBreadcrumb,
  } satisfies ReportOptions;
}
