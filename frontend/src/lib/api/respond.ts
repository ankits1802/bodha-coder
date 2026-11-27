import { request } from "./client";
import type {
  AddendumAnswer,
  CodeSent,
  DocumentLink,
  LevelChangeBody,
  LevelChangeResult,
  OtherRequest,
  ProviderRequest,
  ProviderToken,
  RespondResult,
} from "./types";

export function sendProviderCode(token: string): Promise<CodeSent> {
  return request<CodeSent>("/api/respond/code", { body: { token }, auth: "none" });
}

export function verifyProviderCode(token: string, code: string): Promise<ProviderToken> {
  return request<ProviderToken>("/api/respond/verify", { body: { token, code }, auth: "none" });
}

export function getProviderRequest(providerToken: string): Promise<ProviderRequest> {
  return request<ProviderRequest>("/api/respond", { auth: { bearer: providerToken } });
}

export function getProviderDocument(providerToken: string): Promise<DocumentLink> {
  return request<DocumentLink>("/api/respond/document", { auth: { bearer: providerToken } });
}

export function submitAnswers(providerToken: string, answers: AddendumAnswer[], attestation: string): Promise<RespondResult> {
  return request<RespondResult>("/api/respond", {
    body: { answers, confirmed: true, attestation },
    auth: { bearer: providerToken },
  });
}

export function answerLevelChange(providerToken: string, body: LevelChangeBody): Promise<LevelChangeResult> {
  return request<LevelChangeResult>("/api/respond/level-change", { body, auth: { bearer: providerToken } });
}

export function getOtherRequests(providerToken: string): Promise<OtherRequest[]> {
  return request<OtherRequest[]>("/api/respond/others", { auth: { bearer: providerToken } });
}

export function switchRequest(providerToken: string, requestId: string): Promise<ProviderToken> {
  return request<ProviderToken>("/api/respond/switch", {
    body: { request_id: requestId },
    auth: { bearer: providerToken },
  });
}
