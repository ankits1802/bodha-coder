import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { addProvider, editProvider } from "@/lib/api/practice";
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

  it("offers text messages and the mobile phone under More when texts can be sent", async () => {
    signIn(true);
    render(<ProviderDialog provider={PREFERS_TEXT} places={[]} onClose={vi.fn()} onSaved={vi.fn()} />);

    expect(screen.queryByRole("combobox", { name: "Send questions by" })).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "More" }));
    expect(screen.getByRole("combobox", { name: "Send questions by" })).toHaveTextContent("Text message");
    expect(screen.getByLabelText(/Mobile phone/)).toHaveValue(PHONE);
  });

  it("shows only the name, credential, NPI, usual place and email until More is opened", async () => {
    signIn(false);
    render(<ProviderDialog provider={null} places={[]} onClose={vi.fn()} onSaved={vi.fn()} />);
    const form = screen.getByRole("dialog");
    expect(within(form).getAllByRole("textbox")).toHaveLength(3);
    expect(within(form).getByRole("textbox", { name: "Name" })).toBeInTheDocument();
    expect(within(form).getByRole("textbox", { name: "NPI, optional" })).toBeInTheDocument();
    expect(within(form).getByRole("textbox", { name: "Email" })).toBeInTheDocument();
    expect(within(form).getByRole("combobox", { name: "Credential" })).toBeInTheDocument();
    expect(within(form).getByRole("combobox", { name: "Usual place of service, optional" })).toBeInTheDocument();
    expect(within(form).queryByRole("group", { name: "Credentialing" })).not.toBeInTheDocument();
    const more = within(form).getByRole("button", { name: "More" });
    expect(more).toHaveAttribute("aria-expanded", "false");
    await userEvent.setup().click(more);
    expect(more).toHaveAttribute("aria-expanded", "true");
    expect(within(form).getByRole("group", { name: "Credentialing" })).toBeInTheDocument();
  });

  it("opens More when a field there needs fixing and saves nothing", async () => {
    signIn(false);
    const user = userEvent.setup();
    render(<ProviderDialog provider={null} places={[]} onClose={vi.fn()} onSaved={vi.fn()} />);
    await user.type(screen.getByRole("textbox", { name: "Name" }), "Dana Whitaker");
    await user.type(screen.getByRole("textbox", { name: "Email" }), "dana@clinic.example.com");
    await user.click(screen.getByRole("button", { name: "More" }));
    await user.type(screen.getByLabelText(/License state/), "TX");
    await user.click(screen.getByRole("button", { name: "More" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByRole("button", { name: "More" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Add the license number")).toBeInTheDocument();
    expect(addProvider).not.toHaveBeenCalled();
  });
});
