import { describe, expect, it } from "vitest";
import { nextLaneView } from "../nextLane";
import { queueTotals } from "./fixtures";

const CODER = { lane: "coder", reason: null } as const;
const QUESTIONS = { lane: "provider", reason: "questions" } as const;

describe("the next lane after a lane empties", () => {
  it("stays on the lane while it still has notes", () => {
    expect(nextLaneView(queueTotals({ coder: 2, approve: 5 }), CODER, "coder")).toBeNull();
  });

  it("offers the following lane with work, wrapping round to the first", () => {
    expect(nextLaneView(queueTotals({ approve: 5, provider: 3 }, { questions: 3 }), CODER, "coder")?.key).toBe("questions");
    expect(nextLaneView(queueTotals({ approve: 5 }), CODER, "coder")?.key).toBe("approve");
  });

  it("skips lanes the person cannot work and the lane that only waits on providers", () => {
    const totals = queueTotals({ compliance: 4, provider: 2 }, { waiting_on_provider: 2 });
    expect(nextLaneView(totals, CODER, "coder")).toBeNull();
    expect(nextLaneView(totals, CODER, "admin")?.key).toBe("compliance");
    expect(nextLaneView(queueTotals({ approve: 3, coder: 1 }), QUESTIONS, "cdi")?.key).toBe("coder");
  });

  it("keeps a split of the provider lane apart from its other half", () => {
    const totals = queueTotals({ provider: 2, approve: 1 }, { waiting_on_provider: 2 });
    expect(nextLaneView(totals, QUESTIONS, "coder")?.key).toBe("approve");
  });
});
