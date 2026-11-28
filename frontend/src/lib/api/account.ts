import { request, requestNothing } from "./client";
import type { Appearance, Preferences, RecoveryCodes, RecoveryCodeStatus, SignedInDevice } from "./types";

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

export function getPreferences(): Promise<Preferences> {
  return request<Preferences>("/api/auth/preferences");
}

export function savePreferences(preferences: Preferences): Promise<Preferences> {
  return request<Preferences>("/api/auth/preferences", { method: "PUT", body: preferences });
}

export function getAppearance(): Promise<Appearance> {
  return request<Appearance>("/api/auth/appearance");
}

export function saveAppearance(appearance: Appearance): Promise<Appearance> {
  return request<Appearance>("/api/auth/appearance", { method: "PUT", body: appearance });
}
