import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { getBilling, getExports } from "@/lib/api/billing";
import { downloadClaimFile, getClaimFiles, sendClaims } from "@/lib/api/claims";
import { saveFile } from "@/lib/download";
import { clearSession, setSession } from "@/lib/session/store";
import { BillingScreen } from "../BillingScreen";
import { PORTAL, SFTP, billingWith, claimRow } from "./claimFixtures";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
  usePathname: () => "/billing",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/api/billing", () => ({ getBilling: vi.fn(), downloadClaimLines: vi.fn(), getExports: vi.fn(), downloadExport: vi.fn() }));
vi.mock("@/lib/api/claims", () => ({
  sendClaims: vi.fn(),
  downloadClaimFile: vi.fn(),
  getClaimFiles: vi.fn(),
  downloadStoredClaimFile: vi.fn(),
  uploadAcknowledgment: vi.fn(),
  getClaimDetails: vi.fn(),
  saveClaimDetails: vi.fn(),
}));
vi.mock("@/lib/download", async (importOriginal) => ({ ...(await importOriginal<typeof import("@/lib/download")>()), saveFile: vi.fn() }));

const READY = claimRow("note-ready", { status: "ready", at: null, reasons: [], missing: [] });
const MISSING = claimRow("note-missing", { status: "missing", at: null, reasons: [], missing: ["payer.id", "charge:99214"] });
const REJECTED = claimRow("note-rejected", {
  status: "rejected",
  at: "2026-11-27T10:00:00Z",
  reasons: [{ code: "A7:562:85", text: "rejected for invalid information (status 562)" }],
  missing: [],
});

describe("claims on the billing screen", () => {
  beforeEach(() => {
    setSession({ access_token: "token", user: { ...CODER, role: "biller" } });
    vi.mocked(getExports).mockResolvedValue({ items: [], total: 0, offset: 0, page_size: 50 });
    vi.mocked(getClaimFiles).mockResolvedValue({ items: [], total: 0, offset: 0, page_size: 50 });
  });

  afterEach(() => {
    clearSession();
    vi.mocked(getBilling).mockReset();
    vi.mocked(sendClaims).mockReset();
    vi.mocked(downloadClaimFile).mockReset();
  });

  it("shows each claim's status, what is missing and why it was rejected", async () => {
    vi.mocked(getBilling).mockResolvedValue(billingWith([READY, MISSING, REJECTED], SFTP));
    render(<BillingScreen />);
    const table = await screen.findByRole("table", { name: "Approved visits" });
    expect(within(table).getByRole("columnheader", { name: "Claim" })).toBeInTheDocument();
    expect(within(table).getByText("Missing information")).toBeInTheDocument();
    expect(within(table).getByText("Payer ID, Charge for 99214")).toBeInTheDocument();
    expect(within(table).getByText("Rejected")).toBeInTheDocument();
    expect(within(table).getByText("Rejected for invalid information (status 562)")).toBeInTheDocument();
    expect(within(table).getAllByRole("button", { name: "Claim details for Marisol Reyes" })).toHaveLength(3);
  });

  it("sends the ready and fixed claims over SFTP and keeps the claim lines export as a second choice", async () => {
    vi.mocked(getBilling).mockResolvedValue(billingWith([READY, MISSING, REJECTED], SFTP));
    vi.mocked(sendClaims).mockResolvedValue({ id: "submission-1", claims: 2, outcome: "delivered" });
    render(<BillingScreen />);
    const send = await screen.findByRole("button", { name: "Send 2 claims" });
    expect(screen.getByRole("button", { name: "Download 837P" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /claim lines/ })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Claim files" })).toBeInTheDocument();
    fireEvent.click(send);
    await waitFor(() => expect(sendClaims).toHaveBeenCalledWith(["note-ready", "note-rejected"]));
    expect(await screen.findByText("2 claims sent")).toBeInTheDocument();
  });

  it("offers only the 837P download when the practice uploads to a portal", async () => {
    vi.mocked(getBilling).mockResolvedValue(billingWith([READY], PORTAL));
    const blob = new Blob(["ISA*00*"], { type: "application/edi-x12" });
    vi.mocked(downloadClaimFile).mockResolvedValue({ blob, fileName: "bodha-837p-000000007.txt" });
    render(<BillingScreen />);
    const download = await screen.findByRole("button", { name: "Download 837P" });
    expect(screen.queryByRole("button", { name: /^Send/ })).not.toBeInTheDocument();
    fireEvent.click(download);
    await waitFor(() => expect(downloadClaimFile).toHaveBeenCalledWith(["note-ready"]));
    await waitFor(() => expect(saveFile).toHaveBeenCalledWith(blob, "bodha-837p-000000007.txt"));
    expect(await screen.findByText("Claim file downloaded")).toBeInTheDocument();
  });

  it("hides the claim column and the clearinghouse actions without a clearinghouse", async () => {
    vi.mocked(getBilling).mockResolvedValue(billingWith([{ ...READY, claim: null }], null));
    render(<BillingScreen />);
    const table = await screen.findByRole("table", { name: "Approved visits" });
    expect(within(table).queryByRole("columnheader", { name: "Claim" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Download 837P" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Claim files" })).not.toBeInTheDocument();
  });
});
