import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import { renewPractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { RenewDialog } from "../RenewDialog";

vi.mock("@/lib/api/hq", () => ({ renewPractice: vi.fn() }));

const PRACTICE = {
  id: "p1",
  name: "Lakeside Primary Care",
  renews_on: "2099-01-31",
  time_zone: "America/Chicago",
  plan: "trial",
} as HqPractice;

describe("RenewDialog", () => {
  beforeEach(() => vi.mocked(renewPractice).mockReset());

  it("starts on a year from the current end date and renews to the preset chosen", async () => {
    vi.mocked(renewPractice).mockResolvedValue({ renews_on: "2099-04-30", plan: "trial" });
    const onDone = vi.fn();
    render(<RenewDialog subject={PRACTICE} onDone={onDone} onClose={vi.fn()} />);

    expect(screen.getByRole("radio", { name: "1 year" })).toBeChecked();
    expect(screen.getByText("Ends 31 Jan 2100")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "3 months" }));
    fireEvent.click(screen.getByRole("button", { name: "Renew" }));

    await waitFor(() => expect(renewPractice).toHaveBeenCalledWith("p1", "2099-04-30", "trial"));
    expect(onDone).toHaveBeenCalledWith("Lakeside Primary Care is on Trial until 30 Apr 2099");
  });

  it("renews with no end date", async () => {
    vi.mocked(renewPractice).mockResolvedValue({ renews_on: null, plan: "trial" });
    const onDone = vi.fn();
    render(<RenewDialog subject={PRACTICE} onDone={onDone} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("radio", { name: "No end date" }));
    expect(screen.getAllByText("No end date").length).toBeGreaterThan(1);
    fireEvent.click(screen.getByRole("button", { name: "Renew" }));

    await waitFor(() => expect(renewPractice).toHaveBeenCalledWith("p1", null, "trial"));
    expect(onDone).toHaveBeenCalledWith("Lakeside Primary Care is on Trial with no end date");
  });

  it("changes the plan along with the renewal", async () => {
    vi.mocked(renewPractice).mockResolvedValue({ renews_on: null, plan: "enterprise" });
    const onDone = vi.fn();
    const user = userEvent.setup();
    render(<RenewDialog subject={PRACTICE} onDone={onDone} onClose={vi.fn()} />);

    expect(screen.getByRole("combobox", { name: "Plan" })).toHaveTextContent("Trial");
    await user.click(screen.getByRole("combobox", { name: "Plan" }));
    await user.click(await screen.findByRole("option", { name: "Enterprise" }));
    fireEvent.click(screen.getByRole("radio", { name: "No end date" }));
    fireEvent.click(screen.getByRole("button", { name: "Renew" }));

    await waitFor(() => expect(renewPractice).toHaveBeenCalledWith("p1", null, "enterprise"));
    expect(onDone).toHaveBeenCalledWith("Lakeside Primary Care is on Enterprise with no end date");
  });

  it("shows why the server refused", async () => {
    vi.mocked(renewPractice).mockImplementationOnce(async () => {
      throw new ApiError(409, "conflict", "this practice pays through Stripe; change the plan there");
    });
    render(<RenewDialog subject={PRACTICE} onDone={vi.fn()} onClose={vi.fn()} />);
    const dialog = screen.getByRole("dialog", { name: "Renew Lakeside Primary Care" });

    await userEvent.setup().click(within(dialog).getByRole("button", { name: "Renew" }));

    expect(await within(dialog).findByText(/pays through Stripe/i)).toBeInTheDocument();
  });
});
