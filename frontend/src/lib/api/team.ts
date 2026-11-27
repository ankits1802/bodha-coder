import { request, requestNothing } from "./client";
import type { Created, InviteBody, MemberUpdate, TeamList } from "./types";

const memberPath = (userId: string, suffix = ""): string => `/api/team/${encodeURIComponent(userId)}${suffix}`;

export function getTeam(): Promise<TeamList> {
  return request<TeamList>("/api/team");
}

export function inviteMember(body: InviteBody): Promise<Created> {
  return request<Created>("/api/team", { body });
}

export function updateMember(userId: string, update: MemberUpdate): Promise<void> {
  return requestNothing(memberPath(userId), { method: "PATCH", body: update });
}

export function removeMember(userId: string): Promise<void> {
  return requestNothing(memberPath(userId), { method: "DELETE" });
}

export function resetMemberMfa(userId: string): Promise<void> {
  return requestNothing(memberPath(userId, "/reset-mfa"), { method: "POST" });
}

export function resendInvite(userId: string): Promise<void> {
  return requestNothing(memberPath(userId, "/resend-invite"), { method: "POST" });
}

export function sendPasswordReset(userId: string): Promise<void> {
  return requestNothing(memberPath(userId, "/reset-password"), { method: "POST" });
}
