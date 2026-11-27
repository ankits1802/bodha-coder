import { describe, expect, it } from "vitest";
import { parseView, viewsFor } from "../qualityModel";

describe("quality views", () => {
  it("gives admins the training view, where training is assigned, and keeps it from compliance", () => {
    expect(viewsFor("admin")).toEqual(["audits", "training", "evaluation", "autonomy"]);
    expect(viewsFor("compliance")).toEqual(["audits", "evaluation", "autonomy"]);
    expect(parseView("training", "admin")).toBe("training");
    expect(parseView("training", "compliance")).toBe("audits");
    expect(parseView(null, "admin")).toBe("audits");
  });
});
