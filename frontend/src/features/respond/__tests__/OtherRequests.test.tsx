import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getOtherRequests, getProviderRequest, switchRequest } from "@/lib/api/respond";
import type { OtherRequest, ProviderRequest } from "@/lib/api/types";
import { RequestView } from "../RequestView";

vi.mock("@/lib/api/respond", () => ({
  getProviderRequest: vi.fn(),
  getProviderDocument: vi.fn(),
  submitAnswers: vi.fn(),
  getOtherRequests: vi.fn(),
  switchRequest: vi.fn(),
}));

const ANSWERED: ProviderRequest = {
  practice_name: "Lakeside Primary Care",
  provider_name: "Elena Varga, MD",
  status: "answered",
  patient: { name: "Reyes Marisol", age: 67, sex: "female" },
  service_date: "2026-11-25",
  visit_type: "Established patient",
  place_code: "11",
  place_name: "Office",
  requested_by: "Priya Nair",
  requested_at: "2026-11-26T15:00:00Z",
  answered_at: "2026-11-27T14:00:00Z",
  expires_at: "2026-11-29T15:00:00Z",
  questions: [{ key: "dx:N18.30", text: "What stage is the kidney disease?", context: [], options: ["Yes", "No", "Other"] }],
  texts: [{ revision: 1, source: "document", text: "CKD, stable." }],
  addendum_text: "Addendum by Elena Varga, MD, 27 Nov 2026.\nWhat stage is the kidney disease? Yes.",
};

const PIKE: OtherRequest = {
  id: "request-2",
  patient_name: "Pike Jonah",
  service_date: "2026-11-24",
  sent_at: "2026-11-26T16:00:00Z",
  questions: 2,
};

function renderView(onSwitch = vi.fn()) {
  render(<RequestView providerToken="token-1" onExpired={vi.fn()} onSwitch={onSwitch} />);
  return onSwitch;
}

describe("other requests for the same provider", () => {
  afterEach(() => {
    vi.mocked(getOtherRequests).mockReset();
    vi.mocked(switchRequest).mockReset();
  });

  it("lists the provider's other open requests and opens one with a new session", async () => {
    vi.mocked(getProviderRequest).mockResolvedValue(ANSWERED);
    vi.mocked(getOtherRequests).mockResolvedValue([PIKE]);
    vi.mocked(switchRequest).mockResolvedValue({ provider_token: "token-2" });
    const onSwitch = renderView();

    expect(await screen.findByRole("region", { name: "Other requests" })).toBeInTheDocument();
    expect(screen.getByText("Pike Jonah")).toBeInTheDocument();
    expect(screen.getByText(/2 questions/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open the request about Pike Jonah" }));

    await waitFor(() => expect(onSwitch).toHaveBeenCalledWith("token-2"));
    expect(switchRequest).toHaveBeenCalledWith("token-1", "request-2");
  });

  it("offers the next request once this one is signed", async () => {
    vi.mocked(getProviderRequest).mockResolvedValue(ANSWERED);
    vi.mocked(getOtherRequests).mockResolvedValue([PIKE]);
    vi.mocked(switchRequest).mockResolvedValue({ provider_token: "token-2" });
    const onSwitch = renderView();

    fireEvent.click(await screen.findByRole("button", { name: "Next request" }));
    await waitFor(() => expect(onSwitch).toHaveBeenCalledWith("token-2"));
  });

  it("shows neither the list nor a next request when nothing else is open", async () => {
    vi.mocked(getProviderRequest).mockResolvedValue(ANSWERED);
    vi.mocked(getOtherRequests).mockResolvedValue([]);
    renderView();

    expect(await screen.findByText("Already answered")).toBeInTheDocument();
    await waitFor(() => expect(getOtherRequests).toHaveBeenCalledWith("token-1"));
    expect(screen.queryByRole("region", { name: "Other requests" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Next request" })).not.toBeInTheDocument();
  });
});
