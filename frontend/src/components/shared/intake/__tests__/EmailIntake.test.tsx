import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import {
  allowIntakeSender,
  getEmailIntake,
  getIntakeMessages,
  getIntakeTest,
  issueIntakeAddress,
  removeIntakeSender,
  retireIntakeAddress,
  sendIntakeTest,
} from "@/lib/api/emailIntake";
import { EMAIL_INTAKE_KEY, EmailIntake } from "../EmailIntake";
import { INTAKE_MESSAGES_KEY } from "../IntakeMessages";
import { TEST_POLL_MS } from "../useIntakeTest";
import { ADDRESS, EMPTY_PAGE, NEXT_ADDRESS, OFF, PAGE, RECEIVING } from "./emailIntakeFixtures";

vi.mock("@/lib/api/emailIntake", () => ({
  getEmailIntake: vi.fn(),
  issueIntakeAddress: vi.fn(),
  retireIntakeAddress: vi.fn(),
  allowIntakeSender: vi.fn(),
  removeIntakeSender: vi.fn(),
  sendIntakeTest: vi.fn(),
  getIntakeTest: vi.fn(),
  getIntakeMessages: vi.fn(),
}));

function forget(): void {
  forgetRemote(EMAIL_INTAKE_KEY);
  for (const version of [0, 1]) forgetRemote(`${INTAKE_MESSAGES_KEY}:${version}:0`);
}

describe("EmailIntake", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forget();
    vi.mocked(getEmailIntake).mockResolvedValue(RECEIVING);
    vi.mocked(getIntakeMessages).mockResolvedValue(EMPTY_PAGE);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("says email intake is not available before Bodha has a domain and offers nothing to set up", async () => {
    vi.mocked(getEmailIntake).mockResolvedValue({ ...OFF, available: false });
    render(<EmailIntake />);
    expect(await screen.findByText("Not available")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Get an address" })).not.toBeInTheDocument();
  });

  it("gets an address and copies it", async () => {
    vi.mocked(getEmailIntake).mockResolvedValue(OFF);
    vi.mocked(issueIntakeAddress).mockResolvedValue(RECEIVING);
    const events = userEvent.setup();
    render(<EmailIntake />);
    await events.click(await screen.findByRole("button", { name: "Get an address" }));
    expect(await screen.findByText(ADDRESS)).toBeInTheDocument();
    expect(screen.getByText("Receiving")).toBeInTheDocument();
    await events.click(screen.getByRole("button", { name: "Copy" }));
    expect(await screen.findByText("Copied")).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe(ADDRESS);
  });

  it("replaces the address and turns intake off only after confirming", async () => {
    vi.mocked(issueIntakeAddress).mockResolvedValue({ ...RECEIVING, address: NEXT_ADDRESS });
    vi.mocked(retireIntakeAddress).mockResolvedValue(OFF);
    const events = userEvent.setup();
    render(<EmailIntake />);
    await events.click(await screen.findByRole("button", { name: "New address" }));
    await events.click(within(screen.getByRole("dialog", { name: "Replace this address?" })).getByRole("button", { name: "Replace" }));
    expect(await screen.findByText(NEXT_ADDRESS)).toBeInTheDocument();
    await events.click(screen.getByRole("button", { name: "Turn off" }));
    await events.click(within(screen.getByRole("dialog", { name: "Turn off email intake?" })).getByRole("button", { name: "Turn off" }));
    expect(await screen.findByRole("button", { name: "Get an address" })).toBeInTheDocument();
    expect(retireIntakeAddress).toHaveBeenCalledTimes(1);
  });

  it("allows a sender and removes one", async () => {
    vi.mocked(allowIntakeSender).mockResolvedValue(RECEIVING);
    vi.mocked(removeIntakeSender).mockResolvedValue({ ...RECEIVING, senders: [] });
    const events = userEvent.setup();
    render(<EmailIntake />);
    await events.type(await screen.findByRole("textbox", { name: "Address or domain" }), " scans@riverbend.example.org ");
    await events.click(screen.getByRole("button", { name: "Allow" }));
    expect(allowIntakeSender).toHaveBeenCalledWith("scans@riverbend.example.org");
    await events.click(screen.getByRole("button", { name: "Remove lakeside.example.com" }));
    expect(removeIntakeSender).toHaveBeenCalledWith("s1");
    expect(await screen.findByText("No allowed senders")).toBeInTheDocument();
  });

  it("sends a test and shows when it arrived", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(sendIntakeTest).mockResolvedValue({ id: "t1", sent_at: "2026-11-28T10:00:00Z", arrived_at: null });
    vi.mocked(getIntakeTest).mockResolvedValue({ id: "t1", sent_at: "2026-11-28T10:00:00Z", arrived_at: "2026-11-28T10:00:20Z" });
    const events = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<EmailIntake />);
    await events.click(await screen.findByRole("button", { name: "Send a test" }));
    expect(await screen.findByText("Waiting for the test")).toBeInTheDocument();
    await vi.advanceTimersByTimeAsync(TEST_POLL_MS);
    expect(await screen.findByText(/^Arrived /)).toBeInTheDocument();
    expect(getIntakeTest).toHaveBeenCalledWith("t1");
    await waitFor(() => expect(getIntakeMessages).toHaveBeenCalledTimes(2));
  });

  it("lists what arrived with each outcome and the reasons files were refused, without message contents", async () => {
    vi.mocked(getIntakeMessages).mockResolvedValue(PAGE);
    render(<EmailIntake />);
    const list = await screen.findByRole("list", { name: "Received" });
    expect(within(list).getByText("Accepted 1 file, 1 file refused")).toBeInTheDocument();
    expect(within(list).getByText("Only PDF files are read")).toBeInTheDocument();
    expect(within(list).getByText("Sender not allowed")).toBeInTheDocument();
    expect(within(list).getByText("someone@elsewhere.example.org")).toBeInTheDocument();
  });
});
