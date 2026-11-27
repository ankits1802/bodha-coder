import { request, requestNothing } from "./client";
import type {
  AdminLink,
  DemoRequest,
  DemoRequestRow,
  HqActivityPage,
  HqActivityQuery,
  HqOverview,
  HqPlace,
  HqPractice,
  NewPractice,
  PracticeUpdate,
} from "./types";

export function getHqOverview(): Promise<HqOverview> {
  return request<HqOverview>("/api/hq/overview");
}

export function getHqPractices(): Promise<HqPractice[]> {
  return request<HqPractice[]>("/api/hq/practices");
}

export function addPractice(body: NewPractice): Promise<{ id: string }> {
  return request<{ id: string }>("/api/hq/practices", { body });
}

const practicePath = (practiceId: string, suffix = ""): string => `/api/hq/practices/${encodeURIComponent(practiceId)}${suffix}`;

export function updatePractice(practiceId: string, update: PracticeUpdate): Promise<void> {
  return requestNothing(practicePath(practiceId), { method: "PATCH", body: update });
}

export function sendAdminLink(practiceId: string): Promise<{ sent: AdminLink }> {
  return request<{ sent: AdminLink }>(practicePath(practiceId, "/admin-link"), { method: "POST" });
}

export function renewPractice(practiceId: string): Promise<{ renews_on: string }> {
  return request<{ renews_on: string }>(practicePath(practiceId, "/renew"), { method: "POST" });
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

export function getDemoRequests(): Promise<DemoRequestRow[]> {
  return request<DemoRequestRow[]>("/api/hq/demo-requests");
}

export function requestDemo(body: DemoRequest): Promise<void> {
  return requestNothing("/api/demo-requests", { body, auth: "none" });
}
