import { describe, expect, it } from "vitest";
import type { QueueRow } from "@/lib/api/types";
import { reviewStart } from "../reviewStart";

describe("start reviewing", () => {
  it("opens the first note that needs a coder in the coder lane", () => {
    expect(reviewStart({ next_up: [{ id: "note 1" } as QueueRow] })).toBe("/notes/note%201?lane=coder");
  });

  it("opens the coder lane when nothing waits for a coder", () => {
    expect(reviewStart({ next_up: [] })).toBe("/queue?lane=coder");
  });
});
