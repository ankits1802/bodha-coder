import { request } from "./client";
import type { EhrCheck, EhrConnection, EhrDocumentPage, EhrKeyAlgorithm, EhrPullRunPage, EhrSettingsInput } from "./types";

const EHR_CONNECTION = "/api/practice/ehr-connection";

export function getEhrConnection(): Promise<EhrConnection> {
  return request<EhrConnection>(EHR_CONNECTION);
}

export function saveEhrConnection(settings: EhrSettingsInput): Promise<EhrConnection> {
  return request<EhrConnection>(EHR_CONNECTION, { method: "PUT", body: settings });
}

export function createEhrKey(algorithm: EhrKeyAlgorithm): Promise<EhrConnection> {
  return request<EhrConnection>(`${EHR_CONNECTION}/key`, { body: { algorithm } });
}

export function pauseEhrPulls(): Promise<EhrConnection> {
  return request<EhrConnection>(`${EHR_CONNECTION}/pause`, { method: "POST" });
}

export function resumeEhrPulls(): Promise<EhrConnection> {
  return request<EhrConnection>(`${EHR_CONNECTION}/resume`, { method: "POST" });
}

export function testEhrConnection(): Promise<EhrCheck> {
  return request<EhrCheck>(`${EHR_CONNECTION}/tests`, { method: "POST" });
}

export function getEhrPullRuns(offset: number): Promise<EhrPullRunPage> {
  return request<EhrPullRunPage>(`${EHR_CONNECTION}/runs`, { query: { offset } });
}

export function getEhrDocuments(offset: number): Promise<EhrDocumentPage> {
  return request<EhrDocumentPage>(`${EHR_CONNECTION}/documents`, { query: { offset } });
}
