import { request } from "./client";
import type { AddendumAnswer, OtherRequest, ProviderRequest, RespondResult } from "./types";

export function sendProviderCode(token: string): Promise<{ sent_to: string }> {
  return request<{ sent_to: string }>("/api/respond/code", { body: { token }, auth: "none" });
}

export function verifyProviderCode(token: string, code: string): Promise<{ provider_token: string }> {
  return request<{ provider_token: string }>("/api/respond/verify", { body: { token, code }, auth: "none" });
}

export function getProviderRequest(providerToken: string): Promise<ProviderRequest> {
  return request<ProviderRequest>("/api/respond", { auth: { bearer: providerToken } });
}

export function getProviderDocument(providerToken: string): Promise<{ url: string }> {
  return request<{ url: string }>("/api/respond/document", { auth: { bearer: providerToken } });
}

export function submitAnswers(providerToken: string, answers: AddendumAnswer[]): Promise<RespondResult> {
  return request<RespondResult>("/api/respond", { body: { answers, confirmed: true }, auth: { bearer: providerToken } });
}

export function getOtherRequests(providerToken: string): Promise<OtherRequest[]> {
  return request<OtherRequest[]>("/api/respond/others", { auth: { bearer: providerToken } });
}

export function switchRequest(providerToken: string, requestId: string): Promise<{ provider_token: string }> {
  return request<{ provider_token: string }>("/api/respond/switch", {
    body: { request_id: requestId },
    auth: { bearer: providerToken },
  });
}
