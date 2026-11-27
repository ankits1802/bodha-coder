import { request, requestNothing } from "./client";
import type {
  AdminLinkSent,
  Created,
  DemoRequest,
  DemoRequestRow,
  HqActivityPage,
  HqActivityQuery,
  HqInvite,
  HqMemberUpdate,
  HqOverview,
  HqPlace,
  HqPractice,
  HqTeamMember,
  NewPractice,
  PracticeUpdate,
  Renewal,
} from "./types";

export function getHqOverview(): Promise<HqOverview> {
  return request<HqOverview>("/api/hq/overview");
}

export function getHqPractices(): Promise<HqPractice[]> {
  return request<HqPractice[]>("/api/hq/practices");
}

export function addPractice(body: NewPractice): Promise<Created> {
  return request<Created>("/api/hq/practices", { body });
}

const practicePath = (practiceId: string, suffix = ""): string => `/api/hq/practices/${encodeURIComponent(practiceId)}${suffix}`;

export function updatePractice(practiceId: string, update: PracticeUpdate): Promise<void> {
  return requestNothing(practicePath(practiceId), { method: "PATCH", body: update });
}

export function sendAdminLink(practiceId: string): Promise<AdminLinkSent> {
  return request<AdminLinkSent>(practicePath(practiceId, "/admin-link"), { method: "POST" });
}

export function renewPractice(practiceId: string): Promise<Renewal> {
  return request<Renewal>(practicePath(practiceId, "/renew"), { method: "POST" });
}

export function deletePractice(practiceId: string, confirmName: string): Promise<void> {
  return requestNothing(practicePath(practiceId), { method: "DELETE", body: { confirm_name: confirmName } });
}

export function getHqPlaces(): Promise<HqPlace[]> {
  return request<HqPlace[]>("/api/hq/places");
}

export function setHqPlace(code: string, name: string | null, active: boolean): Promise<void> {
  return requestNothing(`/api/hq/places/${encodeURIComponent(code)}`, { method: "PUT", body: { name, active } });
}

export function getHqActivity(query: HqActivityQuery): Promise<HqActivityPage> {
  return request<HqActivityPage>("/api/hq/activity", { query: { ...query } });
}

const teamPath = (userId: string, suffix = ""): string => `/api/hq/team/${encodeURIComponent(userId)}${suffix}`;

export function getHqTeam(): Promise<HqTeamMember[]> {
  return request<HqTeamMember[]>("/api/hq/team");
}

export function inviteHqMember(body: HqInvite): Promise<Created> {
  return request<Created>("/api/hq/team", { body });
}

export function resendHqInvite(userId: string): Promise<void> {
  return requestNothing(teamPath(userId, "/resend-invite"), { method: "POST" });
}

export function updateHqMember(userId: string, update: HqMemberUpdate): Promise<void> {
  return requestNothing(teamPath(userId), { method: "PATCH", body: update });
}

export function getDemoRequests(): Promise<DemoRequestRow[]> {
  return request<DemoRequestRow[]>("/api/hq/demo-requests");
}

export function requestDemo(body: DemoRequest): Promise<void> {
  return requestNothing("/api/demo-requests", { body, auth: "none" });
}
