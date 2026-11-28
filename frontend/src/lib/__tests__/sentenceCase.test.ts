import { describe, expect, it } from "vitest";
import { sentenceCase } from "../format";

describe("sentenceCase", () => {
  it("starts with a capital and names HQ in capitals", () => {
    expect(sentenceCase("hq member invited")).toBe("HQ member invited");
    expect(sentenceCase("practice renewed by hq")).toBe("Practice renewed by HQ");
    expect(sentenceCase("hq")).toBe("HQ");
  });

  it("leaves hq inside addresses, paths and other words alone", () => {
    expect(sentenceCase("write to hq@bodha.example.com")).toBe("Write to hq@bodha.example.com");
    expect(sentenceCase("open /hq/practices")).toBe("Open /hq/practices");
    expect(sentenceCase("hqx and ahq stay")).toBe("Hqx and ahq stay");
  });
});
