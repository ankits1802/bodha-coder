import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { clearSession, setSession } from "@/lib/session/store";
import { SessionGate } from "../SessionGate";

const navigation = vi.hoisted(() => ({ pathname: "/today", replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));
vi.mock("../useIdleSignOut", () => ({ useIdleSignOut: () => undefined }));

function signInAdmin(billingOnly: boolean): void {
  setSession({ access_token: "token", user: { ...CODER, role: "admin", billing_only: billingOnly } });
}

function renderGate(screenName: string) {
  return render(
    <SessionGate scope="practice">
      <p>{screenName}</p>
    </SessionGate>,
  );
}

describe("SessionGate", () => {
  beforeEach(() => {
    navigation.replace.mockClear();
  });

  afterEach(() => {
    clearSession();
  });

  it("sends a billing-only admin from any other page to the plan screen", async () => {
    navigation.pathname = "/today";
    signInAdmin(true);
    renderGate("Today screen");
    expect(screen.queryByText("Today screen")).not.toBeInTheDocument();
    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/plan"));
  });

  it("keeps a billing-only admin away from a note", async () => {
    navigation.pathname = "/notes/note-1";
    signInAdmin(true);
    renderGate("Note review");
    expect(screen.queryByText("Note review")).not.toBeInTheDocument();
    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/plan"));
  });

  it("opens the plan screen to a billing-only admin", () => {
    navigation.pathname = "/plan";
    signInAdmin(true);
    renderGate("Plan screen");
    expect(screen.getByText("Plan screen")).toBeInTheDocument();
    expect(navigation.replace).not.toHaveBeenCalled();
  });

  it("opens every page again once the session is no longer billing-only", () => {
    navigation.pathname = "/today";
    signInAdmin(true);
    renderGate("Today screen");
    expect(screen.queryByText("Today screen")).not.toBeInTheDocument();
    act(() => signInAdmin(false));
    expect(screen.getByText("Today screen")).toBeInTheDocument();
  });
});
