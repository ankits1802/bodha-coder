import { describe, expect, it } from "vitest";
import type { NoteDetail, NoteStatus } from "@/lib/api/types";
import { reviewPermissions } from "../permissions";

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
});
