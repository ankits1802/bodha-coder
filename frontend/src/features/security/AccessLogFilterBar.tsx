"use client";

import { useState } from "react";
import { DatePicker } from "@/components/ui/DatePicker";
import { SearchField } from "@/components/ui/SearchField";
import { Select } from "@/components/ui/Select";
import type { AccessLogPerson } from "@/lib/api/types";
import type { ResolvedFilters } from "./accessLog";
import { SECURITY_TEXT } from "./strings";

const words = SECURITY_TEXT.log;

interface AccessLogFilterBarProps {
  filters: ResolvedFilters;
  today: string;
  people: AccessLogPerson[];
  actions: string[];
  onChange: (changes: Partial<ResolvedFilters>) => void;
}

function CommitField({ label, value, onCommit }: { label: string; value: string | null; onCommit: (next: string) => void }) {
  const [typed, setTyped] = useState(value ?? "");
  const commit = () => {
    if (typed.trim() !== (value ?? "")) onCommit(typed);
  };
  return (
    <SearchField
      label={label}
      value={typed}
      onChange={(event) => setTyped(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") commit();
      }}
    />
  );
}

function choices(actions: string[], current: string | null): { value: string; label: string }[] {
  const listed = current && !actions.includes(current) ? [...actions, current] : actions;
  return [{ value: "", label: words.anyAction }, ...listed.map((action) => ({ value: action, label: action }))];
}

function personChoices(people: AccessLogPerson[], current: string | null): { value: string; label: string }[] {
  const listed = current && !people.some((person) => person.id === current) ? [...people, { id: current, name: current }] : people;
  return [{ value: "", label: words.anyone }, ...listed.map((person) => ({ value: person.id, label: person.name }))];
}

export function AccessLogFilterBar({ filters, today, people, actions, onChange }: AccessLogFilterBarProps) {
  return (
    <div role="group" aria-label={words.filters} className="flex flex-wrap items-center gap-2 px-4 pb-3">
      <DatePicker variant="filter" label={words.from} value={filters.start} max={filters.end} today={today} onChange={(start) => start && onChange({ start })} />
      <DatePicker variant="filter" label={words.to} value={filters.end} min={filters.start} today={today} onChange={(end) => end && onChange({ end })} />
      <Select
        variant="filter"
        label={words.person}
        value={filters.user_id ?? ""}
        options={personChoices(people, filters.user_id)}
        onChange={(user) => onChange({ user_id: user || null })}
      />
      <Select variant="filter" label={words.action} value={filters.action ?? ""} options={choices(actions, filters.action)} onChange={(action) => onChange({ action: action || null })} />
      <CommitField label={words.note} value={filters.note_id} onCommit={(note) => onChange({ note_id: note })} />
      <CommitField label={words.patient} value={filters.patient} onCommit={(patient) => onChange({ patient })} />
      <DatePicker variant="filter" label={words.birthDate} value={filters.birth_date} max={today} today={today} onChange={(born) => onChange({ birth_date: born })} />
    </div>
  );
}
