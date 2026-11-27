"use client";

import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { LOOKUP_SECONDS } from "@/hooks/remoteCache";
import { useRemote } from "@/hooks/useRemote";
import { getPayers, setNotePayer } from "@/lib/api/notes";
import { REVIEW_TEXT } from "../strings";

interface PayerSelectProps {
  noteId: string;
  payer: string | null;
  onChanged: () => void;
}

export function PayerSelect({ noteId, payer, onChanged }: PayerSelectProps) {
  const payers = useRemote("note-payers", getPayers, LOOKUP_SECONDS);
  const save = useAction((next: string | null) => setNotePayer(noteId, next));
  const options = payers.state.status === "success" ? payers.state.data : [];
  if (options.length === 0) return null;

  async function choose(value: string): Promise<void> {
    if ((await save.run(value || null)).ok) onChanged();
  }

  return (
    <Select
      variant="filter"
      label={REVIEW_TEXT.tools.payer}
      value={payer ?? ""}
      options={[{ value: "", label: REVIEW_TEXT.tools.noPayer }, ...options.map((option) => ({ value: option.id, label: option.name }))]}
      onChange={(value) => void choose(value)}
    />
  );
}
