import { request, requestNothing } from "./client";
import type {
  AdminAppointed,
  AdminAppointment,
  AdminLinkSent,
  AuditVerification,
  Created,
  DemoRequest,
  DemoRequestRow,
  HqActivityPage,
  HqActivityQuery,
  HqExpenditure,
  HqInvite,
  HqMemberUpdate,
  HqOverview,
  HqPlace,
  HqPractice,
  HqTeamMember,
  NewPractice,
  PracticePurged,
  PracticeUpdate,
  Renewal,
  SpendRange,
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

export function appointAdmin(practiceId: string, body: AdminAppointment): Promise<AdminAppointed> {
  return request<AdminAppointed>(practicePath(practiceId, "/admins"), { body });
}

export function renewPractice(practiceId: string, until: string | null): Promise<Renewal> {
  return request<Renewal>(practicePath(practiceId, "/renew"), { method: "POST", body: { until } });
}

export function closePractice(practiceId: string, confirmName: string): Promise<void> {
  return requestNothing(practicePath(practiceId, "/close"), { method: "POST", body: { confirm_name: confirmName } });
}

export function purgePractice(practiceId: string, confirmName: string): Promise<PracticePurged> {
  return request<PracticePurged>(practicePath(practiceId, "/purge"), { body: { confirm_name: confirmName } });
}

export function verifyAuditLog(): Promise<AuditVerification> {
  return request<AuditVerification>("/api/hq/audit-log/verify", { method: "POST" });
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

export function getHqExpenditure(range: SpendRange): Promise<HqExpenditure> {
  return request<HqExpenditure>("/api/hq/expenditure", { query: { from: range.from, to: range.to } });
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
