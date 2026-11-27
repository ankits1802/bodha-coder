import type { InboxEntry, InboxPage } from "@/lib/api/types";

export function inboxEntry(change: Partial<InboxEntry>): InboxEntry {
  return {
    id: "item-1",
    kind: "provider_answered",
    note_id: "note-1",
    actor_name: "Elena Varga",
    payload: { questions: 2 },
    patient_name: "Marisol Reyes",
    service_date: "2026-11-25",
    created_at: "2026-11-27T15:00:00Z",
    read_at: null,
    ...change,
  };
}

export function inboxPage(items: InboxEntry[], unread: number): InboxPage {
  return { items, total: items.length, unread, offset: 0, page_size: 50 };
}
