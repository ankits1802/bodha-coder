"use client";

import { useState } from "react";
import type { ClaimEstimates, PointerLine } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";
import { useClaimPointers } from "../useClaimPointers";
import { ClaimCodes } from "./ClaimEstimate";
import { PointerEditor } from "./PointerEditor";

interface LinkedClaimCodesProps {
  noteId: string;
  claim: string[];
  estimate: ClaimEstimates | null;
  editable: boolean;
}

export function LinkedClaimCodes({ noteId, claim, estimate, editable }: LinkedClaimCodesProps) {
  const links = useClaimPointers(noteId, claim);
  const [editing, setEditing] = useState<PointerLine | null>(null);
  const data = links.state.status === "success" ? links.state.data : null;

  async function save(pointers: string[]): Promise<void> {
    if (editing && (await links.save(editing.code, pointers))) setEditing(null);
  }

  function close(): void {
    links.clearError();
    setEditing(null);
  }

  return (
    <>
      <ClaimCodes claim={claim} estimate={estimate} pointers={data} onEdit={editable && data ? setEditing : null} />
      {links.state.status === "error" ? (
        <span role="alert" className="text-footnote text-bad-text">
          {REVIEW_TEXT.pointers.unavailable}
        </span>
      ) : null}
      {editing && data ? (
        <PointerEditor
          key={editing.code}
          line={editing}
          diagnoses={data.diagnoses}
          pending={links.pending}
          error={links.error}
          onSave={(pointers) => void save(pointers)}
          onClose={close}
        />
      ) : null}
    </>
  );
}
