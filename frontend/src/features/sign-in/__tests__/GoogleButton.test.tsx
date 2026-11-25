import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getSignInProviders } from "@/lib/api/auth";
import { GoogleButton } from "../GoogleButton";

vi.mock("@/lib/api/auth", () => ({ GOOGLE_START_PATH: "/api/auth/google/start", getSignInProviders: vi.fn() }));

describe("GoogleButton", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows nothing when Google sign-in is off", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue({ google: false });
    render(<GoogleButton />);
    await waitFor(() => expect(getSignInProviders).toHaveBeenCalledTimes(1));
    await act(async () => undefined);

    expect(screen.queryByRole("link", { name: "Continue with Google" })).not.toBeInTheDocument();
  });

  it("links to the Google start route when Google sign-in is on", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue({ google: true });
    render(<GoogleButton />);

    const link = await screen.findByRole("link", { name: "Continue with Google" });
    expect(link).toHaveAttribute("href", "/api/auth/google/start");
  });
});
