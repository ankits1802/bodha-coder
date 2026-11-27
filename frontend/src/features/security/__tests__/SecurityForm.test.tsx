import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { refreshSession } from "@/lib/api/client";
import { saveSecurity } from "@/lib/api/practice";
import type { SecuritySettings } from "@/lib/api/types";
import { SecurityForm } from "../SecurityForm";

vi.mock("@/lib/api/practice", () => ({ saveSecurity: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ refreshSession: vi.fn() }));

const SETTINGS: SecuritySettings = { mfa_roles: ["admin", "compliance"], idle_minutes: 15, access_log_years: 6 };

describe("SecurityForm", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(saveSecurity).mockResolvedValue(undefined);
    vi.mocked(refreshSession).mockResolvedValue(true);
  });

  it("keeps the access log for the chosen number of years", async () => {
    const onSaved = vi.fn();
    render(<SecurityForm settings={SETTINGS} onSaved={onSaved} />);
    const keep = screen.getByRole("combobox", { name: "Keep the access log for" });
    expect(keep).toHaveTextContent("6 years");
    fireEvent.click(keep);
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
      "6 years",
      "7 years",
      "8 years",
      "9 years",
      "10 years",
    ]);
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    fireEvent.click(screen.getByRole("option", { name: "10 years" }));
    expect(keep).toHaveTextContent("10 years");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(saveSecurity).toHaveBeenCalledWith({ mfa_roles: ["admin", "compliance"], idle_minutes: 15, access_log_years: 10 });
  });
});
