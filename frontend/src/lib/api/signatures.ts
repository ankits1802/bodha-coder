import { request } from "./client";
import type { MySignature, SealVerification, SignatureDraftBody, SignatureView } from "./types";

export function getMySignature(): Promise<MySignature> {
  return request<MySignature>("/api/signature");
}

export function draftSignature(body: SignatureDraftBody): Promise<SignatureView> {
  return request<SignatureView>("/api/signature/drafts", { body });
}

export function adoptSignature(signatureId: string): Promise<MySignature> {
  return request<MySignature>(`/api/signature/drafts/${encodeURIComponent(signatureId)}/adopt`, { method: "POST" });
}

export function draftProviderSignature(providerToken: string, body: SignatureDraftBody): Promise<SignatureView> {
  return request<SignatureView>("/api/respond/signature/drafts", { body, auth: { bearer: providerToken } });
}

export function verifySeal(code: string): Promise<SealVerification> {
  return request<SealVerification>(`/api/verify/${encodeURIComponent(code)}`, { auth: "none" });
}
