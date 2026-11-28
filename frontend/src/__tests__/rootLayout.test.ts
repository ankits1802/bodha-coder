import { connection } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import RootLayout from "@/app/layout";

const device = vi.hoisted(() => ({ cookies: new Map<string, string>() }));

vi.mock("next/font/google", () => ({ Inter: () => ({ variable: "font-inter" }) }));
vi.mock("next/server", () => ({ connection: vi.fn(async () => undefined) }));
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    get: (name: string) => {
      const value = device.cookies.get(name);
      return value === undefined ? undefined : { name, value };
    },
  })),
}));

describe("RootLayout", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    device.cookies.clear();
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

  it("leaves a device with no kept appearance to its system settings", async () => {
    const page = await RootLayout({ children: null });
    expect(page.props["data-theme"]).toBeUndefined();
    expect(page.props["data-text-size"]).toBeUndefined();
    expect(page.props["data-motion"]).toBeUndefined();
  });

  it("marks the first paint with the appearance kept on the device", async () => {
    device.cookies.set("bodha_appearance", "dark.larger.on");
    const page = await RootLayout({ children: null });
    expect(page.props).toMatchObject({ "data-theme": "dark", "data-text-size": "larger", "data-motion": "reduce" });
  });

  it("ignores a kept appearance it does not recognise", async () => {
    device.cookies.set("bodha_appearance", "neon.huge.fast");
    const page = await RootLayout({ children: null });
    expect(page.props["data-theme"]).toBeUndefined();
    expect(page.props["data-text-size"]).toBeUndefined();
    expect(page.props["data-motion"]).toBeUndefined();
  });
});
