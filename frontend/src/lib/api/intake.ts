import { request } from "./client";
import type { IntakeSettings, IntakeView } from "./types";

export function getIntake(): Promise<IntakeView> {
  return request<IntakeView>("/api/practice/intake");
}

export function saveIntake(settings: IntakeSettings): Promise<IntakeView> {
  return request<IntakeView>("/api/practice/intake", { method: "PUT", body: settings });
}
