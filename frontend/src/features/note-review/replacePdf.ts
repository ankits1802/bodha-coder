import type { NoteStatus, Role } from "@/lib/api/types";
import { canDo } from "@/lib/roles";

const FIXED_DOCUMENT: readonly NoteStatus[] = ["exported", "reading"];

export function canReplacePdf(role: Role | null | undefined, status: NoteStatus): boolean {
  return canDo(role, "manageNotes") && !FIXED_DOCUMENT.includes(status);
}

export function isPdfFile(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}
