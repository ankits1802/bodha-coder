import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { approveJoinRequest, declineJoinRequest, getJoinRequests } from "@/lib/api/domains";
import type { JoinRequestRow } from "@/lib/api/types";
import { JOIN_REQUESTS_KEY, JoinRequestsPanel } from "../JoinRequestsPanel";

vi.mock("@/lib/api/domains", () => ({
  getJoinRequests: vi.fn(),
  approveJoinRequest: vi.fn(),
  declineJoinRequest: vi.fn(),
}));

const DANA: JoinRequestRow = {
  id: "request-1",
  name: "Dana Fox",
  email: "dana@lakeside.example.com",
  domain: "lakeside.example.com",
  suggested_role: "viewer",
  created_at: "2026-11-28T10:00:00Z",
};
const OMAR: JoinRequestRow = { ...DANA, id: "request-2", name: "Omar Haddad", email: "omar@lakeside.example.com" };

describe("JoinRequestsPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote(JOIN_REQUESTS_KEY);
    vi.mocked(getJoinRequests).mockResolvedValue([DANA, OMAR]);
    vi.mocked(approveJoinRequest).mockResolvedValue({ id: "user-9" });
    vi.mocked(declineJoinRequest).mockResolvedValue(undefined);
  });

  it("approves a request with the suggested role or the one chosen", async () => {
    const onChanged = vi.fn();
    const events = userEvent.setup();
    render(<JoinRequestsPanel onChanged={onChanged} />);
    expect(await screen.findByText("dana@lakeside.example.com · lakeside.example.com")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Role for Dana Fox" })).toHaveTextContent("Viewer");
    await events.click(screen.getByRole("combobox", { name: "Role for Dana Fox" }));
    await events.click(screen.getByRole("option", { name: "Coder" }));
    await events.click(screen.getByRole("button", { name: "Approve Dana Fox" }));
    expect(approveJoinRequest).toHaveBeenCalledWith("request-1", "coder");
    expect(await screen.findByText("Dana Fox was invited")).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
    await waitFor(() => expect(getJoinRequests).toHaveBeenCalledTimes(2));
  });

  it("declines a request", async () => {
    const events = userEvent.setup();
    render(<JoinRequestsPanel onChanged={vi.fn()} />);
    await events.click(await screen.findByRole("button", { name: "Decline Omar Haddad" }));
    expect(declineJoinRequest).toHaveBeenCalledWith("request-2");
    expect(await screen.findByText("Request from Omar Haddad declined")).toBeInTheDocument();
  });

  it("stays out of the way when nobody is waiting", async () => {
    vi.mocked(getJoinRequests).mockResolvedValue([]);
    const { container } = render(<JoinRequestsPanel onChanged={vi.fn()} />);
    await waitFor(() => expect(getJoinRequests).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
