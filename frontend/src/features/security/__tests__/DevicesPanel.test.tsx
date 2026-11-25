import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getSignedInDevices, signOutDevice, signOutOtherDevices } from "@/lib/api/account";
import type { SignedInDevice } from "@/lib/api/types";
import { DevicesPanel } from "../DevicesPanel";

vi.mock("@/lib/api/account", () => ({
  getSignedInDevices: vi.fn(),
  signOutDevice: vi.fn(),
  signOutOtherDevices: vi.fn(),
}));

const NOW = new Date().toISOString();
const THIS_MAC: SignedInDevice = {
  id: "session-mac",
  created_at: NOW,
  last_used_at: NOW,
  ip: "203.0.113.7",
  user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
  current: true,
};
const PHONE: SignedInDevice = {
  id: "session-phone",
  created_at: NOW,
  last_used_at: NOW,
  ip: "198.51.100.4",
  user_agent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/604.1",
  current: false,
};

describe("DevicesPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("lists devices and signs out one that is not this device", async () => {
    vi.mocked(getSignedInDevices).mockResolvedValueOnce([THIS_MAC, PHONE]).mockResolvedValue([THIS_MAC]);
    vi.mocked(signOutDevice).mockResolvedValue(undefined);
    render(<DevicesPanel />);

    expect(await screen.findByText("Mac · Safari · 203.0.113.7")).toBeInTheDocument();
    expect(screen.getByText("This device")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out Mac · Safari · 203.0.113.7" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign out iPhone · Safari · 198.51.100.4" }));

    await waitFor(() => expect(signOutDevice).toHaveBeenCalledWith("session-phone"));
    await waitFor(() => expect(screen.queryByText("iPhone · Safari · 198.51.100.4")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Sign out everywhere else" })).toBeDisabled();
  });

  it("signs out every other device at once", async () => {
    vi.mocked(getSignedInDevices).mockResolvedValueOnce([THIS_MAC, PHONE]).mockResolvedValue([THIS_MAC]);
    vi.mocked(signOutOtherDevices).mockResolvedValue(undefined);
    render(<DevicesPanel />);
    await screen.findByText("iPhone · Safari · 198.51.100.4");
    fireEvent.click(screen.getByRole("button", { name: "Sign out everywhere else" }));

    await waitFor(() => expect(signOutOtherDevices).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getSignedInDevices).toHaveBeenCalledTimes(2));
    expect(signOutDevice).not.toHaveBeenCalled();
  });
});
