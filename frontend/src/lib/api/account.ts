import { request, requestNothing } from "./client";
import type { RecoveryCodes, RecoveryCodeStatus, SignedInDevice } from "./types";

export function getSignedInDevices(): Promise<SignedInDevice[]> {
  return request<SignedInDevice[]>("/api/auth/sessions");
}

export function signOutDevice(sessionId: string): Promise<void> {
  return requestNothing(`/api/auth/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export function signOutOtherDevices(): Promise<void> {
  return requestNothing("/api/auth/sessions/end-others", { method: "POST" });
}

export function getRecoveryCodeStatus(): Promise<RecoveryCodeStatus> {
  return request<RecoveryCodeStatus>("/api/auth/recovery-codes");
}

export function replaceRecoveryCodes(code: string): Promise<RecoveryCodes> {
  return request<RecoveryCodes>("/api/auth/recovery-codes", { body: { code } });
}
