import { request, requestNothing } from "./client";
import type {
  DemoRequest,
  DemoRequestRow,
  HqActivityEntry,
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

export function updatePractice(practiceId: string, update: PracticeUpdate): Promise<void> {
  return requestNothing(`/api/hq/practices/${encodeURIComponent(practiceId)}`, { method: "PATCH", body: update });
}

export function getHqPlaces(): Promise<HqPlace[]> {
  return request<HqPlace[]>("/api/hq/places");
}

export function setHqPlace(code: string, name: string | null, active: boolean): Promise<void> {
  return requestNothing(`/api/hq/places/${encodeURIComponent(code)}`, { method: "PUT", body: { name, active } });
}

export function getHqActivity(practiceId: string | null): Promise<HqActivityEntry[]> {
  return request<HqActivityEntry[]>("/api/hq/activity", { query: { practice_id: practiceId } });
}

export function getDemoRequests(): Promise<DemoRequestRow[]> {
  return request<DemoRequestRow[]>("/api/hq/demo-requests");
}

export function requestDemo(body: DemoRequest): Promise<void> {
  return requestNothing("/api/demo-requests", { body, auth: "none" });
}
