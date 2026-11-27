import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { appointAdmin } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { AppointAdminDialog } from "../AppointAdminDialog";

vi.mock("@/lib/api/hq", () => ({ appointAdmin: vi.fn() }));

const PRACTICE = { id: "practice-1", name: "Lakeside" } as HqPractice;
const REASON = "previous admin left; requested by practice owner by email";

describe("AppointAdminDialog", () => {
  beforeEach(() => vi.resetAllMocks());

  it("needs a reason before HQ adds an admin", async () => {
    const user = userEvent.setup();
    render(<AppointAdminDialog practice={PRACTICE} onClose={vi.fn()} onAppointed={vi.fn()} />);
    await user.type(screen.getByLabelText("Name"), "Lee Park");
    await user.type(screen.getByLabelText("Email"), "lee@lakeside.example.com");
    await user.click(screen.getByRole("button", { name: "Add admin" }));
    expect(screen.getByText("Enter a reason")).toBeInTheDocument();
    expect(appointAdmin).not.toHaveBeenCalled();
  });

  it("sends the person and the reason", async () => {
    vi.mocked(appointAdmin).mockResolvedValue({ outcome: "added" });
    const onAppointed = vi.fn();
    const user = userEvent.setup();
    render(<AppointAdminDialog practice={PRACTICE} onClose={vi.fn()} onAppointed={onAppointed} />);
    await user.type(screen.getByLabelText("Name"), "Lee Park");
    await user.type(screen.getByLabelText("Email"), "lee@lakeside.example.com");
    await user.type(screen.getByLabelText("Reason"), REASON);
    await user.click(screen.getByRole("button", { name: "Add admin" }));
    expect(appointAdmin).toHaveBeenCalledWith("practice-1", { name: "Lee Park", email: "lee@lakeside.example.com", reason: REASON });
    await waitFor(() => expect(onAppointed).toHaveBeenCalled());
  });
});
