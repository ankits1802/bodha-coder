import { connection } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import RootLayout from "@/app/layout";

vi.mock("next/font/google", () => ({ Inter: () => ({ variable: "font-inter" }) }));
vi.mock("next/server", () => ({ connection: vi.fn(async () => undefined) }));

describe("RootLayout", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders at request time, so every page carries that request's nonce", async () => {
    await RootLayout({ children: null });
    expect(connection).toHaveBeenCalledTimes(1);
  });

  it("hands the browser its error report settings only when the web DSN is set", async () => {
    const off = await RootLayout({ children: null });
    expect(off.props["data-error-reports"]).toBeUndefined();
    vi.stubEnv("WEB_SENTRY_DSN", "https://0123456789abcdef0123456789abcdef@o1.ingest.us.sentry.io/2");
    vi.stubEnv("APP_VERSION", "4f2a9c1");
    const on = await RootLayout({ children: null });
    expect(JSON.parse(on.props["data-error-reports"])).toMatchObject({ release: "4f2a9c1" });
  });
});
