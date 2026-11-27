import { messageOf } from "@/lib/api/errors";
import { inviteMember } from "@/lib/api/team";
import type { InviteRow } from "./inviteRows";

export interface InviteOutcome {
  sent: number;
  failed: InviteRow[];
}

export async function sendInvites(rows: readonly InviteRow[]): Promise<InviteOutcome> {
  let sent = 0;
  const failed: InviteRow[] = [];
  for (const row of rows) {
    try {
      await inviteMember({ name: row.name.trim(), email: row.email.trim(), role: row.role });
      sent += 1;
    } catch (error) {
      failed.push({ ...row, failure: messageOf(error) });
    }
  }
  return { sent, failed };
}
