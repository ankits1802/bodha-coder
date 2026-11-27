import { request } from "./client";
import type { TourBody, TourKey, TourRecord } from "./types";

export function getTours(): Promise<TourRecord[]> {
  return request<TourRecord[]>("/api/account/tours");
}

export function saveTour(tour: TourKey, body: TourBody): Promise<TourRecord> {
  return request<TourRecord>(`/api/account/tours/${encodeURIComponent(tour)}`, { method: "PUT", body });
}
