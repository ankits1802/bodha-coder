import type { IntakeView } from "@/lib/api/types";
import { INTAKE_TEXT } from "./strings";

export interface FolderRow {
  id: number;
  folder: string;
  providerId: string;
}

export interface IntakeDraft {
  enabled: boolean;
  prefix: string;
  folders: FolderRow[];
  placeCode: string;
  visitType: string;
}

export interface DraftProblems {
  folders: Record<number, string>;
  place: string | null;
  general: string | null;
}

const FOLDER_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,59}$/;
const RESERVED_FOLDERS = ["processed", "rejected"];

export function draftFrom(view: IntakeView): IntakeDraft {
  return {
    enabled: view.enabled,
    prefix: view.prefix,
    folders: Object.entries(view.provider_by_folder).map(([folder, providerId], index) => ({ id: index, folder, providerId })),
    placeCode: view.place_code ?? "",
    visitType: view.visit_type,
  };
}

export function settingsFrom(draft: IntakeDraft): IntakeView {
  return {
    enabled: draft.enabled,
    prefix: draft.prefix,
    provider_by_folder: Object.fromEntries(draft.folders.map((row) => [row.folder.trim(), row.providerId])),
    place_code: draft.placeCode || null,
    visit_type: draft.visitType,
  };
}

function folderProblem(row: FolderRow, names: string[]): string | null {
  const name = row.folder.trim();
  if (!FOLDER_NAME.test(name)) return INTAKE_TEXT.errors.folderName;
  if (RESERVED_FOLDERS.includes(name.toLowerCase())) return INTAKE_TEXT.errors.reserved;
  if (names.filter((other) => other === name).length > 1) return INTAKE_TEXT.errors.duplicate;
  if (!row.providerId) return INTAKE_TEXT.errors.provider;
  return null;
}

export function problemsOf(draft: IntakeDraft): DraftProblems {
  const names = draft.folders.map((row) => row.folder.trim());
  const folders: Record<number, string> = {};
  for (const row of draft.folders) {
    const problem = folderProblem(row, names);
    if (problem) folders[row.id] = problem;
  }
  return {
    folders,
    place: draft.enabled && !draft.placeCode ? INTAKE_TEXT.errors.place : null,
    general: draft.enabled && draft.folders.length === 0 ? INTAKE_TEXT.errors.folders : null,
  };
}

export function hasProblems(problems: DraftProblems): boolean {
  return Object.keys(problems.folders).length > 0 || problems.place !== null || problems.general !== null;
}

export function nextRowId(rows: FolderRow[]): number {
  return rows.reduce((highest, row) => Math.max(highest, row.id), -1) + 1;
}
