import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getAppearance } from "@/lib/api/account";
import { APPEARANCE_COOKIE } from "@/lib/appearance";
import { clearSession, setSession } from "@/lib/session/store";
import { AppearanceSync } from "../AppearanceSync";

vi.mock("@/lib/api/account", () => ({ getAppearance: vi.fn() }));

const ATTRIBUTES = ["data-theme", "data-text-size", "data-motion"];

function signIn(): void {
  setSession({
    access_token: "token",
    user: { id: "user-1", name: "Priya Nair", email: "priya@example.com", role: "coder", billing_only: false, practice: null, practices: [] },
  });
}

describe("AppearanceSync", () => {
  afterEach(() => {
    clearSession();
    vi.mocked(getAppearance).mockReset();
    for (const name of ATTRIBUTES) document.documentElement.removeAttribute(name);
    document.cookie = `${APPEARANCE_COOKIE}=; Path=/; Max-Age=0`;
  });

  it("brings the person's saved appearance to this device once they are signed in", async () => {
    vi.mocked(getAppearance).mockResolvedValue({ theme: "dark", text_size: "larger", reduce_motion: "on" });
    signIn();
    render(<AppearanceSync />);

    await waitFor(() => expect(document.documentElement).toHaveAttribute("data-theme", "dark"));
    expect(document.documentElement).toHaveAttribute("data-text-size", "larger");
    expect(document.documentElement).toHaveAttribute("data-motion", "reduce");
    expect(document.cookie).toContain(`${APPEARANCE_COOKIE}=dark.larger.on`);
  });

  it("asks for nothing before sign-in", () => {
    render(<AppearanceSync />);
    expect(getAppearance).not.toHaveBeenCalled();
  });

  it("keeps this device's appearance when the saved one cannot be read", async () => {
    document.documentElement.setAttribute("data-theme", "light");
    vi.mocked(getAppearance).mockRejectedValue(new TypeError("offline"));
    signIn();
    render(<AppearanceSync />);

    await waitFor(() => expect(getAppearance).toHaveBeenCalledTimes(1));
    await Promise.resolve();
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });
});
