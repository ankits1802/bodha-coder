import type { Instrumentation } from "next";
import { reportSettingsFrom } from "@/lib/errorReports/settings";

export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const settings = reportSettingsFrom(process.env);
  if (!settings) return;
  const { startServerReports } = await import("@/lib/errorReports/server");
  startServerReports(settings);
}

export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  if (process.env.NEXT_RUNTIME !== "nodejs" || !reportSettingsFrom(process.env)) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.captureRequestError(error, request, context);
};
