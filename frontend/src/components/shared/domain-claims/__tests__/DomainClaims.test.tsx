import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import {
  checkDomainRecord,
  claimDomain,
  emailDomainAdmin,
  getDomainClaims,
  releaseDomain,
  setDomainJoin,
  type DomainScope,
} from "@/lib/api/domains";
import { ApiError } from "@/lib/api/errors";
import type { DomainClaim } from "@/lib/api/types";
import { DomainClaims } from "../DomainClaims";

vi.mock("@/lib/api/domains", () => ({
  domainScopeKey: () => "domains:test",
  getDomainClaims: vi.fn(),
  claimDomain: vi.fn(),
  checkDomainRecord: vi.fn(),
  emailDomainAdmin: vi.fn(),
  setDomainJoin: vi.fn(),
  releaseDomain: vi.fn(),
}));

const SCOPE: DomainScope = { kind: "organization", organizationId: "org-1" };
const PRACTICES = [
  { id: "practice-1", name: "Lakeside Primary Care" },
  { id: "practice-2", name: "Riverbend Clinic" },
];
const PENDING: DomainClaim = {
  id: "claim-1",
  domain: "acme.example.com",
  practice_id: "practice-1",
  practice_name: "Lakeside Primary Care",
  verified: false,
  verified_at: null,
  verified_via: null,
  txt_record: "bodha-verify=0123456789abcdef0123456789abcdef",
  email_sent_to: null,
  join_mode: "off",
  join_role: "viewer",
  created_at: "2026-11-28T10:00:00Z",
};
const VERIFIED: DomainClaim = {
  ...PENDING,
  id: "claim-2",
  domain: "acmehealth.example.org",
  verified: true,
  verified_at: "2026-11-28T11:00:00Z",
  verified_via: "dns",
  txt_record: null,
};

async function choose(combobox: string, option: string, events = userEvent.setup()): Promise<void> {
  await events.click(screen.getByRole("combobox", { name: combobox }));
  await events.click(screen.getByRole("option", { name: option }));
}

describe("DomainClaims", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote("domains:test");
    vi.mocked(getDomainClaims).mockResolvedValue([PENDING, VERIFIED]);
    vi.mocked(claimDomain).mockResolvedValue({ id: "claim-3" });
    vi.mocked(checkDomainRecord).mockResolvedValue(undefined);
    vi.mocked(emailDomainAdmin).mockResolvedValue(undefined);
    vi.mocked(setDomainJoin).mockResolvedValue(undefined);
    vi.mocked(releaseDomain).mockResolvedValue(undefined);
  });

  it("claims a domain for the practice people will join", async () => {
    const events = userEvent.setup();
    render(<DomainClaims scope={SCOPE} practices={PRACTICES} />);
    await screen.findByText("acme.example.com");
    await events.type(screen.getByRole("textbox", { name: "Domain" }), "acme.example.net");
    await choose("Practice people join", "Riverbend Clinic", events);
    await events.click(screen.getByRole("button", { name: "Claim" }));
    expect(claimDomain).toHaveBeenCalledWith(SCOPE, { domain: "acme.example.net", practice_id: "practice-2" });
    await waitFor(() => expect(getDomainClaims).toHaveBeenCalledTimes(2));
  });

  it("shows why a public email domain cannot be claimed beside the field", async () => {
    vi.mocked(claimDomain).mockRejectedValue(new ApiError(422, "invalid", "public email services such as gmail.com cannot be claimed"));
    const events = userEvent.setup();
    render(<DomainClaims scope={{ kind: "practice" }} />);
    const field = screen.getByRole("textbox", { name: "Domain" });
    await events.type(field, "gmail.com");
    await events.click(screen.getByRole("button", { name: "Claim" }));
    expect(await screen.findByText("Public email services such as gmail.com cannot be claimed")).toBeInTheDocument();
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByRole("combobox", { name: "Practice people join" })).not.toBeInTheDocument();
  });

  it("shows the TXT record, checks DNS and emails an admin address", async () => {
    const events = userEvent.setup();
    render(<DomainClaims scope={SCOPE} practices={PRACTICES} />);
    expect(await screen.findByText(PENDING.txt_record ?? "")).toBeInTheDocument();
    await events.click(screen.getByRole("button", { name: "Check DNS" }));
    expect(checkDomainRecord).toHaveBeenCalledWith(SCOPE, "claim-1");
    await choose("Admin address at acme.example.com", "postmaster@", events);
    await events.click(screen.getByRole("button", { name: "Send email" }));
    expect(emailDomainAdmin).toHaveBeenCalledWith(SCOPE, "claim-1", "postmaster");
  });

  it("lets people from a verified domain join automatically, never as admins", async () => {
    const events = userEvent.setup();
    render(<DomainClaims scope={SCOPE} practices={PRACTICES} />);
    await screen.findByText("acmehealth.example.org");
    await choose("Joining from acmehealth.example.org", "Join automatically", events);
    const role = screen.getByRole("combobox", { name: "Role for people from acmehealth.example.org" });
    expect(role).toHaveTextContent("Viewer");
    await events.click(role);
    expect(screen.queryByRole("option", { name: "Admin" })).not.toBeInTheDocument();
    await events.click(screen.getByRole("option", { name: "Coder" }));
    await events.click(screen.getByRole("button", { name: "Save" }));
    expect(setDomainJoin).toHaveBeenCalledWith(SCOPE, "claim-2", { mode: "auto", role: "coder" });
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("releases a domain after confirming", async () => {
    const events = userEvent.setup();
    render(<DomainClaims scope={SCOPE} practices={PRACTICES} />);
    await events.click(await screen.findByRole("button", { name: "Release acme.example.com" }));
    const dialog = screen.getByRole("dialog", { name: "Release acme.example.com?" });
    await events.click(within(dialog).getByRole("button", { name: "Release" }));
    expect(releaseDomain).toHaveBeenCalledWith(SCOPE, "claim-1");
  });
});
