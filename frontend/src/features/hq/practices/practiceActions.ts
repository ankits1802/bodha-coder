import { deletePractice, renewPractice, sendAdminLink, updatePractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { HQ_TEXT } from "../strings";

export type PracticeActionKind = "block" | "unblock" | "adminLink" | "renew" | "delete";

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

export function canDeletePractice(practice: Pick<HqPractice, "status">): boolean {
  return practice.status === "ended" || practice.status === "blocked";
}

export function canSendAdminLink(practice: Pick<HqPractice, "admin_status">): boolean {
  return practice.admin_status === "invited" || practice.admin_status === "active";
}

export function adminLinkLabel(practice: Pick<HqPractice, "admin_status">): string {
  return practice.admin_status === "invited" ? words.menu.adminInvite : words.menu.adminReset;
}

export function confirmsDeletion(practice: Pick<HqPractice, "name">, typed: string): boolean {
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
  if (kind === "delete") {
    await deletePractice(practice.id, confirmName);
    return notices.deleted(practice.name);
  }
  const { sent } = await sendAdminLink(practice.id);
  const email = practice.admin_email ?? "";
  return sent === "invite" ? notices.inviteSent(email) : notices.resetSent(email);
}
