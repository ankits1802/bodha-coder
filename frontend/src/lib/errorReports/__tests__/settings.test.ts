import { describe, expect, it } from "vitest";
import { decodeSettings, encodeSettings, ingestOrigin, reportSettingsFrom } from "../settings";

const DSN = "https://0123456789abcdef0123456789abcdef@o1.ingest.us.sentry.io/2";

describe("reportSettingsFrom", () => {
  it("stays off without a DSN", () => {
    expect(reportSettingsFrom({})).toBeNull();
    expect(reportSettingsFrom({ WEB_SENTRY_DSN: "  " })).toBeNull();
  });

  it("tags the release with APP_VERSION", () => {
    expect(reportSettingsFrom({ WEB_SENTRY_DSN: DSN, APP_VERSION: "4f2a9c1" })).toEqual({
      dsn: DSN,
      release: "4f2a9c1",
      environment: "production",
    });
  });

  it("refuses a DSN that is not a Sentry https address", () => {
    expect(() => reportSettingsFrom({ WEB_SENTRY_DSN: "http://key@sentry.example.com/1" })).toThrow("WEB_SENTRY_DSN");
  });
});

describe("page settings", () => {
  it("reads back what the layout writes and ignores anything else", () => {
    const settings = { dsn: DSN, release: "4f2a9c1", environment: "production" };
    expect(decodeSettings(encodeSettings(settings) ?? null)).toEqual(settings);
    expect(encodeSettings(null)).toBeUndefined();
    expect(decodeSettings('{"dsn":"https://evil.example.com"}')).toBeNull();
    expect(decodeSettings("not json")).toBeNull();
  });

  it("names the ingest origin without the key", () => {
    expect(ingestOrigin(DSN)).toBe("https://o1.ingest.us.sentry.io");
  });
});
