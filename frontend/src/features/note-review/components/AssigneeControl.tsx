"use client";

import { useState } from "react";
import { ASSIGNABLE_STATUSES } from "@/components/shared/noteStatus";
import { Button } from "@/components/ui/Button";
import { FilterSelect } from "@/components/ui/FilterSelect";
import { useAction } from "@/hooks/useAction";
import { useAssignees, type Assignee } from "@/hooks/useAssignees";
import { assignNotes } from "@/lib/api/notes";
import type { NoteHeader, User } from "@/lib/api/types";
import { canDo } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { REVIEW_TEXT } from "../strings";

const words = REVIEW_TEXT.tools;

interface PickerProps {
  user: User;
  current: Assignee | null;
  pending: boolean;
  onPick: (person: Assignee | null) => void;
}

function assigneeOf(note: NoteHeader): Assignee | null {
  return note.assigned_to ? { id: note.assigned_to, name: note.assignee_name ?? "" } : null;
}

function PersonPicker({ user, current, pending, onPick }: PickerProps) {
  const assignees = useAssignees(user);
  const known = current && !assignees.people.some((person) => person.id === current.id);
  const people = known && current ? [current, ...assignees.people] : assignees.people;
  return (
    <span className="flex items-center gap-2">
      <span aria-hidden="true" className="text-subhead text-secondary">
        {words.assignee}
      </span>
      <FilterSelect
        label={words.assignee}
        value={current?.id ?? ""}
        disabled={pending}
        onChange={(event) => onPick(people.find((person) => person.id === event.target.value) ?? null)}
      >
        <option value="">{words.nobody}</option>
        {people.map((person) => (
          <option key={person.id} value={person.id}>
            {person.name}
          </option>
        ))}
      </FilterSelect>
      {assignees.error ? <span className="text-footnote text-bad-text">{assignees.error}</span> : null}
    </span>
  );
}

function AssigneeView({ note, user }: { note: NoteHeader; user: User }) {
  const [current, setCurrent] = useState<Assignee | null>(() => assigneeOf(note));
  const assign = useAction(assignNotes);
  const editable = canDo(user.role, "assign") && ASSIGNABLE_STATUSES.includes(note.status);
  const mine = current?.id === user.id;

  async function change(person: Assignee | null): Promise<void> {
    if ((await assign.run([note.id], person?.id ?? null)).ok) setCurrent(person);
  }

  const failure = assign.error ? (
    <span role="alert" className="text-footnote text-bad-text">
      {assign.error}
    </span>
  ) : null;
  if (editable && canDo(user.role, "assignAnyone")) {
    return (
      <>
        <PersonPicker user={user} current={current} pending={assign.pending} onPick={(person) => void change(person)} />
        {failure}
      </>
    );
  }
  return (
    <span className="flex flex-wrap items-center gap-2">
      <span className="text-subhead text-secondary">{current ? words.assignedTo(current.name) : words.unassigned}</span>
      {editable && !current ? (
        <Button size="sm" variant="plain" pending={assign.pending} onClick={() => void change({ id: user.id, name: user.name })}>
          {words.assignToMe}
        </Button>
      ) : null}
      {editable && mine ? (
        <Button size="sm" variant="plain" pending={assign.pending} onClick={() => void change(null)}>
          {words.unassign}
        </Button>
      ) : null}
      {failure}
    </span>
  );
}

export function AssigneeControl({ note }: { note: NoteHeader }) {
  const { user } = useSession();
  return user ? <AssigneeView note={note} user={user} /> : null;
}
