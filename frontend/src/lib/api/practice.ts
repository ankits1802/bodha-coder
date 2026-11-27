import { request, requestNothing } from "./client";
import type {
  AccessLogPage,
  Checks,
  Created,
  ImportedProviders,
  MipsChoice,
  MipsOverview,
  PayerInput,
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

export function addProvider(provider: ProviderInput): Promise<Created> {
  return request<Created>("/api/providers", { body: provider });
}

export function editProvider(providerId: string, provider: ProviderInput): Promise<void> {
  return requestNothing(`/api/providers/${encodeURIComponent(providerId)}`, { method: "PUT", body: provider });
}

export function importProviders(csv: string): Promise<ImportedProviders> {
  return request<ImportedProviders>("/api/providers/import", { body: { csv } });
}

export function getMips(): Promise<MipsOverview> {
  return request<MipsOverview>("/api/mips");
}

export function saveMips(measureIds: string[], expectedMeasureIds: string[]): Promise<MipsChoice> {
  return request<MipsChoice>("/api/mips", {
    method: "PUT",
    body: { measure_ids: measureIds, expected_measure_ids: expectedMeasureIds },
  });
}

export function getAccessLog(day: string | null, userId: string | null, offset: number): Promise<AccessLogPage> {
  return request<AccessLogPage>("/api/access-log", { query: { day, user_id: userId, offset } });
}

const payerPath = (payerId: string): string => `/api/practice/payers/${encodeURIComponent(payerId)}`;

export function addPayer(payer: PayerInput): Promise<Created> {
  return request<Created>("/api/practice/payers", { body: payer });
}

export function changePayer(payerId: string, payer: PayerInput): Promise<void> {
  return requestNothing(payerPath(payerId), { method: "PUT", body: payer });
}

export function removePayer(payerId: string): Promise<void> {
  return requestNothing(payerPath(payerId), { method: "DELETE" });
}
