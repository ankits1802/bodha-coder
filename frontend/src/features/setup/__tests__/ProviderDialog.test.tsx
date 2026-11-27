import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { editProvider } from "@/lib/api/practice";
import type { Provider, User } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { ProviderDialog } from "../ProviderDialog";

vi.mock("@/lib/api/practice", () => ({ addProvider: vi.fn(), editProvider: vi.fn() }));

const PHONE = "+15555550142";

const PREFERS_TEXT: Provider = {
  id: "prov-1",
  name: "Elena Varga",
  credential: "MD",
  specialty: null,
  npi: "1234567893",
  place_code: null,
  email: "varga@clinic.example.com",
  phone: PHONE,
  channel: "sms",
  active: true,
  details: {
    taxonomy_code: null,
    license_number: null,
    license_state: null,
    dea_number: null,
    bills_under: null,
    group_npi: null,
    supervising_physician: null,
    signature_on_file: false,
  },
};

function signIn(canSendTexts: boolean): void {
  const user: User = {
    id: "user-1",
    name: "Practice Admin",
    email: "admin@lakeside.example.com",
    role: "admin",
    billing_only: false,
    practice: {
      id: "practice-1",
      name: "Lakeside Primary Care",
      checks: { em: true, icd: true, cdi: true, audit: true, mips: false, hcc: false },
      can_send_texts: canSendTexts,
      idle_minutes: 15,
      time_zone: "America/Chicago",
    },
    practices: [],
  };
  setSession({ access_token: "token", user });
}

describe("ProviderDialog", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    clearSession();
  });

  it("asks for no mobile phone and saves questions by email while texts cannot be sent", async () => {
    signIn(false);
    vi.mocked(editProvider).mockResolvedValue(undefined);
    const onSaved = vi.fn();
    render(<ProviderDialog provider={PREFERS_TEXT} places={[]} onClose={vi.fn()} onSaved={onSaved} />);

    expect(screen.queryByRole("combobox", { name: "Send questions by" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Mobile phone/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(editProvider).toHaveBeenCalledWith("prov-1", expect.objectContaining({ channel: "email", phone: PHONE }));
  });

  it("offers text messages and the mobile phone when texts can be sent", () => {
    signIn(true);
    render(<ProviderDialog provider={PREFERS_TEXT} places={[]} onClose={vi.fn()} onSaved={vi.fn()} />);

    expect(screen.getByRole("combobox", { name: "Send questions by" })).toHaveTextContent("Text message");
    expect(screen.getByLabelText(/Mobile phone/)).toHaveValue(PHONE);
  });
});
