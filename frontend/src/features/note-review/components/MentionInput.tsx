"use client";

import { useId, useRef, useState, type KeyboardEvent } from "react";
import { Field } from "@/components/ui/Field";
import { TextArea } from "@/components/ui/Input";
import type { CommentPerson } from "@/lib/api/types";
import { activeMention, insertMention, matchingPeople } from "../mentions";

interface MentionInputProps {
  label: string;
  value: string;
  maxLength: number;
  people: CommentPerson[];
  onChange: (value: string) => void;
  onMention: (person: CommentPerson) => void;
  onSubmit: () => void;
}

export function MentionInput({ label, value, maxLength, people, onChange, onMention, onSubmit }: MentionInputProps) {
  const listId = useId();
  const area = useRef<HTMLTextAreaElement>(null);
  const [caret, setCaret] = useState(0);
  const [active, setActive] = useState(0);
  const [closed, setClosed] = useState(false);
  const mention = closed ? null : activeMention(value, caret);
  const options = mention ? matchingPeople(people, mention.query) : [];
  const open = options.length > 0;

  function choose(person: CommentPerson): void {
    if (!mention) return;
    const edit = insertMention(value, mention, caret, person);
    onChange(edit.text);
    onMention(person);
    setCaret(edit.caret);
    requestAnimationFrame(() => area.current?.setSelectionRange(edit.caret, edit.caret));
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      onSubmit();
    } else if (open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      setActive((current) => (current + (event.key === "ArrowDown" ? 1 : options.length - 1)) % options.length);
    } else if (open && event.key === "Enter") {
      event.preventDefault();
      const person = options[Math.min(active, options.length - 1)];
      if (person) choose(person);
    } else if (open && event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      setClosed(true);
    }
  }

  return (
    <div className="relative">
      <Field label={label}>
        {(control) => (
          <TextArea
            {...control}
            ref={area}
            rows={2}
            maxLength={maxLength}
            value={value}
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={open}
            aria-controls={listId}
            aria-activedescendant={open ? `${listId}-${Math.min(active, options.length - 1)}` : undefined}
            onKeyDown={onKeyDown}
            onChange={(event) => {
              onChange(event.target.value);
              setCaret(event.target.selectionStart ?? event.target.value.length);
              setActive(0);
              setClosed(false);
            }}
            onSelect={(event) => setCaret(event.currentTarget.selectionStart ?? 0)}
          />
        )}
      </Field>
      <ul id={listId} role="listbox" hidden={!open} className="absolute z-10 mt-1 w-full max-w-80 list-none rounded-field bg-surface p-1 shadow-dialog">
        {options.map((person, index) => (
          <li
            key={person.id}
            id={`${listId}-${index}`}
            role="option"
            aria-selected={index === Math.min(active, options.length - 1)}
            onMouseDown={(event) => {
              event.preventDefault();
              choose(person);
            }}
            className="cursor-pointer rounded-control px-2.5 py-1.5 text-subhead aria-selected:bg-row-selected"
          >
            {person.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
