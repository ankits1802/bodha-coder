import { request } from "./client";
import type { IntakeView } from "./types";

export function getIntake(): Promise<IntakeView> {
  return request<IntakeView>("/api/practice/intake");
}

export function saveIntake(settings: IntakeView): Promise<IntakeView> {
  return request<IntakeView>("/api/practice/intake", { method: "PUT", body: settings });
}
