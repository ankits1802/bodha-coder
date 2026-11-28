import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAppearance, saveAppearance } from "@/lib/api/account";
import type { Appearance } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";

const CHOSEN: Appearance = { theme: "dark", text_size: "large", reduce_motion: "on" };

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

describe("the appearance API", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    setSession({
      access_token: "token",
      user: { id: "hq-1", name: "Jordan Diaz", email: "jordan@bodha.example.com", role: "hq", billing_only: false, practice: null, practices: [] },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearSession();
  });

  it("reads the signed-in person's appearance", async () => {
    fetchMock.mockResolvedValueOnce(json(CHOSEN));
    await expect(getAppearance()).resolves.toEqual(CHOSEN);
    const [path, init] = fetchMock.mock.calls[0] ?? [];
    expect(path).toBe("/api/auth/appearance");
    expect(init?.method).toBe("GET");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer token");
  });

  it("replaces the whole appearance with the person's choice", async () => {
    fetchMock.mockResolvedValueOnce(json(CHOSEN));
    await expect(saveAppearance(CHOSEN)).resolves.toEqual(CHOSEN);
    const [path, init] = fetchMock.mock.calls[0] ?? [];
    expect(path).toBe("/api/auth/appearance");
    expect(init?.method).toBe("PUT");
    expect(JSON.parse(String(init?.body))).toEqual({ theme: "dark", text_size: "large", reduce_motion: "on" });
  });
});
