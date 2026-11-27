import { describe, expect, it } from "vitest";
import type { AddendumRequestView, NoteDetail, NoteStatus } from "@/lib/api/types";
import { askableQuestions } from "../findings";
import { reviewPermissions } from "../permissions";
import { finding, noteDetail } from "./fixtures";

function detail(status: NoteStatus, read = true): NoteDetail {
  return { note: { status, lane: null }, findings: [], requests: [], analysis: read ? {} : null } as unknown as NoteDetail;
}

describe("reviewPermissions", () => {
  it("lets an approver reopen an approved note but not an exported one", () => {
    expect(reviewPermissions("coder", detail("approved")).reopen).toBe(true);
    expect(reviewPermissions("coder", detail("exported")).reopen).toBe(false);
    expect(reviewPermissions("biller", detail("approved")).reopen).toBe(false);
  });

  it("offers to read again only a note that could not be read", () => {
    expect(reviewPermissions("coder", detail("failed")).retry).toBe(true);
    expect(reviewPermissions("coder", detail("ready")).retry).toBe(false);
  });

  it("lets a coder void only a note Bodha never read and an admin any note not being read", () => {
    expect(reviewPermissions("coder", detail("queued", false)).voidNote).toBe(true);
    expect(reviewPermissions("coder", detail("failed", false)).voidNote).toBe(true);
    expect(reviewPermissions("coder", detail("failed", true)).voidNote).toBe(false);
    expect(reviewPermissions("coder", detail("ready")).voidNote).toBe(false);
    expect(reviewPermissions("admin", detail("exported")).voidNote).toBe(true);
    expect(reviewPermissions("admin", detail("reading")).voidNote).toBe(false);
    expect(reviewPermissions("admin", detail("voided")).voidNote).toBe(false);
    expect(reviewPermissions("cdi", detail("queued", false)).voidNote).toBe(false);
  });

  it("lets only an admin restore a voided note", () => {
    expect(reviewPermissions("admin", detail("voided")).restore).toBe(true);
    expect(reviewPermissions("coder", detail("voided")).restore).toBe(false);
    expect(reviewPermissions("admin", detail("ready")).restore).toBe(false);
  });

  it("lets uploaders change the visit type until the note is approved", () => {
    expect(reviewPermissions("coder", detail("approved")).editVisitType).toBe(false);
    expect(reviewPermissions("admin", detail("failed")).editVisitType).toBe(true);
    expect(reviewPermissions("admin", detail("voided")).editVisitType).toBe(false);
  });

  it("hides Ask while a request already sent covers every open question", () => {
    const stage = finding({ kind: "cdi_query", key: "cdiq-1", action: "ask", code_before: null, choice: "ask", allowed: ["ask", "skip"] });
    const laterality = finding({ ...stage, key: "cdiq-2" });
    const sent = { status: "sent", questions: [{ key: "cdiq-1" }] } as AddendumRequestView;
    const answered = { status: "answered", questions: [{ key: "cdiq-2" }] } as AddendumRequestView;
    expect(askableQuestions([stage, laterality], [sent]).map((item) => item.key)).toEqual(["cdiq-2"]);
    expect(reviewPermissions("coder", noteDetail([stage, laterality], { requests: [sent] })).ask).toBe(true);
    expect(reviewPermissions("coder", noteDetail([stage], { requests: [sent] })).ask).toBe(false);
    expect(reviewPermissions("coder", noteDetail([stage], { requests: [answered] })).ask).toBe(true);
    expect(reviewPermissions("coder", noteDetail([stage])).ask).toBe(true);
  });
});
