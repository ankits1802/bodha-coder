import * as Sentry from "@sentry/nextjs";
import { keptIntegrations, reportOptions, SERVER_INTEGRATIONS } from "./options";
import type { ReportSettings } from "./settings";

export function startServerReports(settings: ReportSettings): void {
  Sentry.init({
    ...reportOptions(settings),
    enableOpenTelemetrySetup: false,
    integrations: keptIntegrations(SERVER_INTEGRATIONS),
  });
}
