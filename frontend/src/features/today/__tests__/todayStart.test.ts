import { describe, expect, it } from "vitest";
import type { BatchProgress, QueueRow } from "@/lib/api/types";
import { hasNotes, myNextNote, startFor } from "../todayStart";

function row(id: string, assigned: string | null): QueueRow {
  return { id, assigned_to: assigned } as QueueRow;
}

const ME = "user-1";
const BUSY = { waiting: 3, batches: [], next_up: [row("note 1", "user-2"), row("note-2", null), row("note-3", ME)] };
const EMPTY = { waiting: 0, batches: [], next_up: [] };

describe("Today's main button", () => {
  it("opens a coder's own next note first, then an unassigned one, then their work in the coder lane", () => {
    expect(startFor("coder", BUSY, ME)).toEqual({ kind: "review", href: "/notes/note-3?lane=coder", noteId: "note-3" });
    const unassigned = { ...BUSY, next_up: [row("note 1", "user-2"), row("note 2", null)] };
    expect(startFor("coder", unassigned, ME)?.href).toBe("/notes/note%202?lane=coder");
    expect(startFor("coder", EMPTY, ME)).toEqual({ kind: "review", href: "/queue?lane=coder&assigned=me", noteId: null });
  });

  it("sends CDI to the questions to send, compliance to its list and billers to ready to bill", () => {
    expect(startFor("cdi", BUSY, ME)).toEqual({ kind: "questions", href: "/queue?lane=provider", noteId: null });
    expect(startFor("compliance", BUSY, ME)).toEqual({ kind: "compliance", href: "/compliance", noteId: null });
    expect(startFor("biller", BUSY, ME)).toEqual({ kind: "billing", href: "/billing", noteId: null });
    expect(startFor("viewer", BUSY, ME)).toBeNull();
  });

  it("gives an admin no review button until the practice has notes, then the first note needing a coder", () => {
    expect(startFor("admin", EMPTY, ME)).toBeNull();
    expect(startFor("admin", BUSY, ME)).toEqual({ kind: "review", href: "/notes/note%201?lane=coder", noteId: "note 1" });
    const reading = { ...EMPTY, batches: [{ id: "batch-1" } as BatchProgress] };
    expect(hasNotes(reading)).toBe(true);
    expect(startFor("admin", reading, ME)).toEqual({ kind: "review", href: "/queue?lane=coder", noteId: null });
  });

  it("finds no note of mine when every note is someone else's", () => {
    expect(myNextNote([row("note-1", "user-2")], ME)).toBeNull();
  });
});
