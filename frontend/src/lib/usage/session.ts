import type { User } from "@/lib/api/types";
import { getSession } from "@/lib/session/store";
import { UsageRecorder } from "./recorder";

export function recordingKey(user: User | null): string | null {
  if (!user || user.role === "hq" || user.billing_only || !user.practice) return null;
  return `${user.id}:${user.practice.id}`;
}

export const usageRecorder = new UsageRecorder({
  clock: () => performance.now(),
  newId: () => crypto.randomUUID(),
  sessionKey: () => recordingKey(getSession().user),
});
