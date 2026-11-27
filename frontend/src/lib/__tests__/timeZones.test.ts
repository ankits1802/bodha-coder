import { describe, expect, it } from "vitest";
import { preferredTimeZone, zoneOptions } from "../timeZones";

describe("zoneOptions", () => {
  it("keeps a zone outside the short list selectable", () => {
    const zones = zoneOptions("Europe/London");
    expect(zones.options).toContain("Europe/London");
    expect(zones.labels["Europe/London"]).toBe("Europe/London");
    expect(zoneOptions("America/Chicago").options).not.toContain("Europe/London");
  });
});

describe("preferredTimeZone", () => {
  it("uses the browser's zone when it is one of the listed zones", () => {
    expect(preferredTimeZone("America/Denver")).toBe("America/Denver");
  });

  it("falls back to Central time for a zone outside the list", () => {
    expect(preferredTimeZone("Europe/London")).toBe("America/Chicago");
    expect(preferredTimeZone("")).toBe("America/Chicago");
  });
});
