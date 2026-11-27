"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import { TextButton } from "@/components/ui/TextButton";
import type { DayFlag, DayNote, ProviderDay } from "@/lib/api/types";
import { FORMAT_WORDS } from "@/lib/format";
import { FLAG_TONES, clonedWith, dayFacts, noteHref } from "./dayFacts";
import { DAY_TEXT } from "./strings";

export function DayFlags({ flags }: { flags: DayFlag[] }) {
  if (flags.length === 0) return <StatusDot tone="ok">{DAY_TEXT.clear}</StatusDot>;
  return (
    <>
      {flags.map((flag) => (
        <StatusDot key={flag} tone={FLAG_TONES[flag]}>
          {DAY_TEXT.flags[flag]}
        </StatusDot>
      ))}
    </>
  );
}

function OtherNote({ note, cloned }: { note: DayNote; cloned: boolean }) {
  return (
    <li className="inline-flex flex-wrap items-center gap-2">
      <Link href={noteHref(note.id)} className="font-medium hover:underline">
        {note.patient_name ?? DAY_TEXT.untitled}
      </Link>
      <span className="text-secondary tabular-nums">{note.em_code ?? FORMAT_WORDS.empty}</span>
      {cloned ? <StatusDot tone={FLAG_TONES.cloned_text}>{DAY_TEXT.flags.cloned_text}</StatusDot> : null}
    </li>
  );
}

interface DayBannerViewProps {
  day: ProviderDay;
  noteId: string;
}

export function DayBannerView({ day, noteId }: DayBannerViewProps) {
  const listId = useId();
  const [open, setOpen] = useState(false);
  const partners = clonedWith(day, noteId);
  const others = day.notes.filter((note) => note.id !== noteId);
  return (
    <Panel aria-label={DAY_TEXT.bannerLabel} className="flex flex-col gap-2.5 px-4.5 py-3.5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <h2 className="m-0 font-sans text-callout font-semibold">{DAY_TEXT.title}</h2>
        <DayFlags flags={day.flags} />
        <span className="text-subhead text-secondary tabular-nums">{dayFacts(day).join(" · ")}</span>
      </div>
      {others.length > 0 ? (
        <TextButton className="self-start text-footnote" aria-expanded={open} aria-controls={listId} onClick={() => setOpen(!open)}>
          {DAY_TEXT.showOthers(others.length)}
        </TextButton>
      ) : null}
      {open && others.length > 0 ? (
        <ul id={listId} aria-label={DAY_TEXT.otherNotes} className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1.5 p-0 text-subhead">
          {others.map((note) => (
            <OtherNote key={note.id} note={note} cloned={partners.has(note.id)} />
          ))}
        </ul>
      ) : null}
    </Panel>
  );
}
