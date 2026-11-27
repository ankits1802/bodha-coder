import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { login } from "@/lib/api/auth";
import { onSessionEnded, request } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { User } from "@/lib/api/types";
import { clearSession, getAccessToken, setSession } from "@/lib/session/store";

const coder: User = {
  id: "u1",
  name: "Priya Nair",
  email: "priya@example.com",
  role: "coder",
  billing_only: false,
  practice: { id: "p1", name: "Lakeside", checks: { em: true, icd: true, cdi: true, audit: true, mips: false, hcc: false }, can_send_texts: true, idle_minutes: 15, time_zone: "America/Chicago" },
};

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function authorizationOf(call: unknown[] | undefined): string | null {
  const init = call?.[1] as RequestInit | undefined;
  return new Headers(init?.headers).get("Authorization");
}

describe("API client session handling", () => {
  const fetchMock = vi.fn<typeof fetch>();
  const ended = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    ended.mockReset();
    onSessionEnded(ended);
    setSession({ access_token: "old-token", user: coder });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearSession();
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    fetchMock
      .mockResolvedValueOnce(json(401, { error: "unauthorized", message: "session expired" }))
      .mockResolvedValueOnce(json(200, { access_token: "new-token", user: coder }))
      .mockResolvedValueOnce(json(200, { waiting: 3 }));

    await expect(request("/api/today")).resolves.toEqual({ waiting: 3 });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/auth/refresh");
    expect(authorizationOf(fetchMock.mock.calls[0])).toBe("Bearer old-token");
    expect(authorizationOf(fetchMock.mock.calls[2])).toBe("Bearer new-token");
    expect(ended).not.toHaveBeenCalled();
  });

  it("ends the session and redirects when the refresh is refused", async () => {
    fetchMock
      .mockResolvedValueOnce(json(401, { error: "unauthorized", message: "session expired" }))
      .mockResolvedValueOnce(json(401, { error: "unauthorized", message: "sign in again" }));

    await expect(request("/api/today")).rejects.toMatchObject({ status: 401 });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(ended).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
  });

  it("does not refresh a second time when the retry is also refused", async () => {
    fetchMock
      .mockResolvedValueOnce(json(401, { error: "unauthorized", message: "session expired" }))
      .mockResolvedValueOnce(json(200, { access_token: "new-token", user: coder }))
      .mockResolvedValueOnce(json(401, { error: "unauthorized", message: "session ended" }));

    await expect(request("/api/today")).rejects.toBeInstanceOf(ApiError);

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls.filter((call) => call[0] === "/api/auth/refresh")).toHaveLength(1);
    expect(ended).toHaveBeenCalledTimes(1);
  });

  it("shares one refresh between requests rejected at the same time", async () => {
    let refreshed = false;
    fetchMock.mockImplementation(async (input) => {
      if (input === "/api/auth/refresh") {
        refreshed = true;
        return json(200, { access_token: "new-token", user: coder });
      }
      return refreshed ? json(200, { path: input }) : json(401, { error: "unauthorized", message: "session expired" });
    });

    const results = await Promise.all([request("/api/today"), request("/api/compliance")]);

    expect(results).toEqual([{ path: "/api/today" }, { path: "/api/compliance" }]);
    expect(fetchMock.mock.calls.filter((call) => call[0] === "/api/auth/refresh")).toHaveLength(1);
    expect(ended).not.toHaveBeenCalled();
  });

  it("never refreshes for sign-in requests and shows the server message", async () => {
    clearSession();
    fetchMock.mockResolvedValueOnce(json(401, { error: "unauthorized", message: "email or password is not correct" }));

    await expect(login("priya@example.com", "wrong-password")).rejects.toMatchObject({
      status: 401,
      message: "email or password is not correct",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(ended).not.toHaveBeenCalled();
  });
});
