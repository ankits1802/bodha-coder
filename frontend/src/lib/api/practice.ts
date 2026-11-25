import { request, requestNothing } from "./client";
import type {
  AccessLogEntry,
  Checks,
  MipsOverview,
  PracticeSetup,
  ProviderInput,
  SecuritySettings,
  SetupSectionKey,
} from "./types";

export function getSetup(): Promise<PracticeSetup> {
  return request<PracticeSetup>("/api/practice/setup");
}

export function saveSetupSection(section: SetupSectionKey, values: Record<string, string>): Promise<void> {
  return requestNothing(`/api/practice/setup/${encodeURIComponent(section)}`, { method: "PUT", body: { values } });
}

export function saveChecks(checks: Checks): Promise<void> {
  return requestNothing("/api/practice/checks", { method: "PUT", body: { checks } });
}

export function saveSecurity(settings: SecuritySettings): Promise<void> {
  return requestNothing("/api/practice/security", { method: "PUT", body: settings });
}

export function addProvider(provider: ProviderInput): Promise<{ id: string }> {
  return request<{ id: string }>("/api/providers", { body: provider });
}

export function editProvider(providerId: string, provider: ProviderInput): Promise<void> {
  return requestNothing(`/api/providers/${encodeURIComponent(providerId)}`, { method: "PUT", body: provider });
}

export function importProviders(csv: string): Promise<{ imported: number }> {
  return request<{ imported: number }>("/api/providers/import", { body: { csv } });
}

export function getMips(): Promise<MipsOverview> {
  return request<MipsOverview>("/api/mips");
}

export function saveMips(measureIds: string[], expectedMeasureIds: string[]): Promise<{ measure_ids: string[] }> {
  return request<{ measure_ids: string[] }>("/api/mips", {
    method: "PUT",
    body: { measure_ids: measureIds, expected_measure_ids: expectedMeasureIds },
  });
}

export function getAccessLog(day: string | null, userId: string | null): Promise<AccessLogEntry[]> {
  return request<AccessLogEntry[]>("/api/access-log", { query: { day, user_id: userId } });
}
