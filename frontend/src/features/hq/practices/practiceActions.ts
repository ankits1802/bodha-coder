import { closePractice, purgePractice, renewPractice, sendAdminLink, updatePractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { localIsoDate } from "@/lib/dates";
import { formatCalendarDay, formatCount } from "@/lib/format";
import { HQ_TEXT } from "../strings";

export type PracticeActionKind = "block" | "unblock" | "adminLink" | "renew" | "close" | "purge";
export type TypedActionKind = Extract<PracticeActionKind, "close" | "purge">;

export interface PracticeAction {
  kind: PracticeActionKind;
  practice: HqPractice;
}

export interface ConfirmWords {
  title: string;
  description?: string;
  confirm: string;
  destructive: boolean;
}

const words = HQ_TEXT.practices;

export function canClosePractice(practice: Pick<HqPractice, "status">): boolean {
  return practice.status === "ended" || practice.status === "blocked";
}

export function canPurgePractice(practice: Pick<HqPractice, "status" | "purge_after">, today: string = localIsoDate()): boolean {
  return practice.status === "closed" && practice.purge_after !== null && today >= practice.purge_after;
}

export function isTypedAction(kind: PracticeActionKind): kind is TypedActionKind {
  return kind === "close" || kind === "purge";
}

export function canSendAdminLink(practice: Pick<HqPractice, "admin_status">): boolean {
  return practice.admin_status === "invited" || practice.admin_status === "active";
}

export function adminLinkLabel(practice: Pick<HqPractice, "admin_status">): string {
  return practice.admin_status === "invited" ? words.menu.adminInvite : words.menu.adminReset;
}

export function confirmsName(practice: Pick<HqPractice, "name">, typed: string): boolean {
  return typed.trim() === practice.name;
}

export function confirmWords({ kind, practice }: PracticeAction): ConfirmWords {
  const confirm = words.confirm;
  const admin = practice.admin_name ?? practice.name;
  if (kind === "block") return { title: confirm.block(practice.name), description: confirm.blockDescription, confirm: confirm.blockAction, destructive: true };
  if (kind === "unblock") return { title: confirm.unblock(practice.name), description: confirm.unblockDescription, confirm: confirm.unblockAction, destructive: false };
  if (kind === "renew") return { title: confirm.renew(practice.name), confirm: confirm.renewAction, destructive: false };
  const title = practice.admin_status === "invited" ? confirm.adminInvite(admin) : confirm.adminReset(admin);
  return { title, description: practice.admin_email ?? undefined, confirm: confirm.sendAction, destructive: false };
}

export async function runPracticeAction({ kind, practice }: PracticeAction, confirmName = ""): Promise<string | null> {
  const notices = words.notices;
  if (kind === "block" || kind === "unblock") {
    await updatePractice(practice.id, { status: kind === "block" ? "blocked" : "active" });
    return null;
  }
  if (kind === "renew") {
    const { renews_on } = await renewPractice(practice.id);
    return notices.renewed(practice.name, formatCalendarDay(renews_on, "year"));
  }
  if (kind === "close") {
    await closePractice(practice.id, confirmName);
    return notices.closed(practice.name);
  }
  if (kind === "purge") {
    const { access_log_entries } = await purgePractice(practice.id, confirmName);
    return notices.purged(practice.name, formatCount(access_log_entries));
  }
  const { sent } = await sendAdminLink(practice.id);
  const email = practice.admin_email ?? "";
  return sent === "invite" ? notices.inviteSent(email) : notices.resetSent(email);
}
