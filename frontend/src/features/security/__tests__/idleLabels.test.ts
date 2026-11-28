import { describe, expect, it } from "vitest";
import { SECURITY_TEXT } from "../strings";

describe("sign-out after inactivity labels", () => {
  it("names each choice in minutes, hours or days", () => {
    expect([15, 30, 60, 240, 480, 1440, 10_080].map(SECURITY_TEXT.minutes)).toEqual([
      "15 minutes",
      "30 minutes",
      "1 hour",
      "4 hours",
      "8 hours",
      "1 day",
      "7 days",
    ]);
  });
});
