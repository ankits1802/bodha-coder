import { request } from "./client";
import type { InboxCount, InboxPage } from "./types";

export function getInbox(offset: number): Promise<InboxPage> {
  return request<InboxPage>("/api/inbox", { query: { offset } });
}

export function getInboxCount(): Promise<InboxCount> {
  return request<InboxCount>("/api/inbox/count");
}

export function markInboxRead(ids: string[]): Promise<InboxCount> {
  return request<InboxCount>("/api/inbox/read", { body: { ids } });
}

export function markAllInboxRead(): Promise<InboxCount> {
  return request<InboxCount>("/api/inbox/read", { body: { all: true } });
}
