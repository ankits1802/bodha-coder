import type { StatusTone } from "@/components/ui/StatusDot";
import { sentence } from "@/lib/api/errors";
import type { IntakeMessage } from "@/lib/api/types";
import { EMAIL_INTAKE_TEXT } from "./strings";

const words = EMAIL_INTAKE_TEXT;

export function messageSummary(message: IntakeMessage): string {
  if (message.outcome === "test") return words.testMessage;
  if (message.outcome === "accepted") {
    const accepted = words.accepted(message.accepted_files);
    return message.refused_files > 0 ? `${accepted}, ${words.alsoRefused(message.refused_files).toLowerCase()}` : accepted;
  }
  return message.reason ? words.reasons[message.reason] : words.reasons.files_refused;
}

export function messageTone(message: IntakeMessage): StatusTone {
  if (message.outcome === "refused") return "bad";
  return message.refused_files > 0 ? "warn" : "ok";
}

export function refusedReasons(message: IntakeMessage): string[] {
  const reasons = message.files.flatMap((file) => (file.outcome === "refused" && file.reason ? [sentence(file.reason)] : []));
  return [...new Set(reasons)];
}
