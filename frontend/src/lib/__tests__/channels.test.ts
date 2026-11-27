import { describe, expect, it } from "vitest";
import { isOfferedChannel, usableChannel } from "../channels";

describe("question channels", () => {
  it("offers text messages only when texts can be sent", () => {
    expect(isOfferedChannel("sms", false)).toBe(false);
    expect(isOfferedChannel("email", false)).toBe(true);
    expect(isOfferedChannel("sms", true)).toBe(true);
  });

  it("moves a provider who prefers texts to email while texts cannot be sent", () => {
    expect(usableChannel("sms", false)).toBe("email");
    expect(usableChannel("sms", true)).toBe("sms");
    expect(usableChannel("email", true)).toBe("email");
  });
});
