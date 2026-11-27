import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getPreferences, savePreferences } from "@/lib/api/account";
import type { Role } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { DigestPreferencePanel } from "../DigestPreferencePanel";

vi.mock("@/lib/api/account", () => ({ getPreferences: vi.fn(), savePreferences: vi.fn() }));

function signIn(role: Role): void {
  setSession({ access_token: "token", user: { id: "user-1", name: "Priya Nair", email: "priya@example.com", role, practice: null } });
}

describe("DigestPreferencePanel", () => {
  afterEach(() => {
    clearSession();
    vi.mocked(getPreferences).mockReset();
    vi.mocked(savePreferences).mockReset();
  });

  it("turns the daily summary email off", async () => {
    signIn("coder");
    vi.mocked(getPreferences).mockResolvedValue({ notify_digest: true });
    vi.mocked(savePreferences).mockResolvedValue({ notify_digest: false });
    render(<DigestPreferencePanel />);

    const toggle = await screen.findByRole("switch", { name: "Email me a daily summary" });
    expect(toggle).toHaveAttribute("aria-checked", "true");
    fireEvent.click(toggle);
    await waitFor(() => expect(savePreferences).toHaveBeenCalledWith({ notify_digest: false }));
    await waitFor(() => expect(screen.getByRole("switch", { name: "Email me a daily summary" })).toHaveAttribute("aria-checked", "false"));
  });

  it("is not offered to a role that gets no summary", () => {
    signIn("viewer");
    render(<DigestPreferencePanel />);
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(getPreferences).not.toHaveBeenCalled();
  });
});
