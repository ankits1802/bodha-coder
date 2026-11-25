"use client";

import { useState } from "react";
import { useAction } from "@/hooks/useAction";
import { exportClaims } from "@/lib/api/billing";
import { saveFile } from "@/lib/download";
import { formatCount } from "@/lib/format";
import { BILLING_TEXT } from "./strings";

export interface ExportAction {
  exportAll: (visits: number) => Promise<void>;
  downloadAgain: (noteIds: string[]) => Promise<void>;
  pending: boolean;
  error: string | null;
  notice: string | null;
}

export function useExport(onExported: () => void): ExportAction {
  const action = useAction(exportClaims);
  const [notice, setNotice] = useState<string | null>(null);

  async function exportAll(visits: number): Promise<void> {
    setNotice(null);
    const outcome = await action.run(null);
    if (!outcome.ok) return;
    saveFile(outcome.value.blob, outcome.value.fileName ?? BILLING_TEXT.defaultFileName);
    setNotice(BILLING_TEXT.exported(formatCount(visits)));
    onExported();
  }

  async function downloadAgain(noteIds: string[]): Promise<void> {
    setNotice(null);
    const outcome = await action.run(noteIds, true);
    if (outcome.ok) saveFile(outcome.value.blob, outcome.value.fileName ?? BILLING_TEXT.defaultFileName);
  }

  return { exportAll, downloadAgain, pending: action.pending, error: action.error, notice };
}
