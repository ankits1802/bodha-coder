"use client";

import { useEffect, useState } from "react";
import { SearchField } from "@/components/ui/SearchField";
import { QUEUE_TEXT } from "../strings";

const DEBOUNCE_MS = 300;

interface QueueSearchProps {
  value: string;
  onSearch: (value: string) => void;
}

export function QueueSearch({ value, onSearch }: QueueSearchProps) {
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    if (draft.trim() === value) return;
    const timer = setTimeout(() => onSearch(draft.trim()), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [draft, value, onSearch]);

  return (
    <SearchField
      label={QUEUE_TEXT.search}
      value={draft}
      maxLength={100}
      onChange={(event) => setDraft(event.target.value)}
    />
  );
}
