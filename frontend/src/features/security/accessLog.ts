import type { AccessLogEntry } from "@/lib/api/types";
import { toCsv } from "@/lib/download";
import { SECURITY_TEXT } from "./strings";

function firstMatch(agent: string, table: readonly (readonly [string, string])[]): string | null {
  const found = table.find(([marker]) => agent.includes(marker));
  return found ? found[1] : null;
}

export function deviceOf(entry: Pick<AccessLogEntry, "ip" | "user_agent">): string {
  const words = SECURITY_TEXT.devices;
  const agent = entry.user_agent ?? "";
  const parts = [firstMatch(agent, words.systems), firstMatch(agent, words.browsers), entry.ip].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : words.unknown;
}

export function accessLogCsv(entries: AccessLogEntry[]): string {
  const rows = entries.map((entry) => [
    entry.at,
    entry.actor,
    entry.actor_kind,
    entry.action,
    entry.detail,
    entry.note_id,
    entry.ip,
    entry.user_agent,
  ]);
  return toCsv([...SECURITY_TEXT.log.csvHeader], rows);
}
