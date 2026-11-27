"use client";

import { FilterSelect } from "@/components/ui/FilterSelect";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getPayers, setNotePayer } from "@/lib/api/notes";
import { REVIEW_TEXT } from "../strings";

interface PayerSelectProps {
  noteId: string;
  payer: string | null;
  onChanged: () => void;
}

export function PayerSelect({ noteId, payer, onChanged }: PayerSelectProps) {
  const payers = useRemote("note-payers", getPayers);
  const save = useAction((next: string | null) => setNotePayer(noteId, next));
  const options = payers.state.status === "success" ? payers.state.data : [];
  if (options.length === 0) return null;

  async function choose(value: string): Promise<void> {
    if ((await save.run(value || null)).ok) onChanged();
  }

  return (
    <FilterSelect label={REVIEW_TEXT.tools.payer} value={payer ?? ""} onChange={(event) => void choose(event.target.value)}>
      <option value="">{REVIEW_TEXT.tools.noPayer}</option>
      {options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.name}
        </option>
      ))}
    </FilterSelect>
  );
}
