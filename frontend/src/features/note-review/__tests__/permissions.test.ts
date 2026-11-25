import { describe, expect, it } from "vitest";
import type { NoteDetail, NoteStatus } from "@/lib/api/types";
import { reviewPermissions } from "../permissions";

function detail(status: NoteStatus): NoteDetail {
  return { note: { status, lane: null }, findings: [], requests: [] } as unknown as NoteDetail;
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
});
