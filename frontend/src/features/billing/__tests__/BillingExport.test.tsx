import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { downloadClaimLines, getBilling, getExports } from "@/lib/api/billing";
import type { BillingList, BillingRow } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { clearSession, setSession } from "@/lib/session/store";
import { BillingScreen } from "../BillingScreen";

const search = vi.hoisted(() => ({ value: "" }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search.value),
  usePathname: () => "/billing",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/api/billing", () => ({ getBilling: vi.fn(), downloadClaimLines: vi.fn(), getExports: vi.fn(), downloadExport: vi.fn() }));
vi.mock("@/lib/download", async (importOriginal) => ({ ...(await importOriginal<typeof import("@/lib/download")>()), saveFile: vi.fn() }));

const ROW: BillingRow = {
  id: "note-1",
  approved_at: "2026-11-26T15:00:00Z",
  approved_by: "Priya Nair",
  changed: 0,
  codes: ["99214", "I10"],
  cpt: ["99214"],
  estimate: 128.4,
  exported_at: null,
  held: false,
  icd10: ["I10"],
  npi: "1234567893",
  patient_name: "Marisol Reyes",
  place_code: "11",
  provider_name: "Elena Varga",
  service_date: "2026-11-25",
  snapshot_id: "snapshot-1",
  snapshot_revision: 1,
  claim: null,
};

function billing(items: BillingRow[]): BillingList {
  return {
    items,
    clearinghouse: null,
    limit: 500,
    offset: 0,
    page_size: 100,
    summary: { exported_today: 0, held_for_provider: 0, ready: items.length },
    total: 2,
  };
}

describe("exporting claim lines", () => {
  beforeEach(() => {
    setSession({ access_token: "token", user: { ...CODER, role: "biller" } });
    vi.mocked(getBilling).mockResolvedValue(billing([ROW, { ...ROW, id: "note-2" }]));
    vi.mocked(getExports).mockResolvedValue({ items: [], total: 0, offset: 0, page_size: 50 });
  });

  afterEach(() => {
    clearSession();
    vi.mocked(getBilling).mockReset();
    vi.mocked(downloadClaimLines).mockReset();
    vi.mocked(saveFile).mockReset();
    search.value = "";
  });

  it("offers one export, as CSV by default, and marks the visits exported", async () => {
    const blob = new Blob(["date_of_service\n"], { type: "text/csv" });
    vi.mocked(downloadClaimLines).mockResolvedValue({ blob, fileName: "bodha-claim-lines-20261128-0900.csv" });
    render(<BillingScreen />);
    const exportButton = await screen.findByRole("button", { name: "Export 2 claim lines" });
    expect(screen.queryByRole("button", { name: /Download .* again/ })).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Format" })).toHaveTextContent("CSV");
    fireEvent.click(exportButton);
    await waitFor(() => expect(downloadClaimLines).toHaveBeenCalledWith("csv"));
    await waitFor(() => expect(saveFile).toHaveBeenCalledWith(blob, "bodha-claim-lines-20261128-0900.csv"));
    expect(await screen.findByText("2 visits exported")).toBeInTheDocument();
    expect(getBilling).toHaveBeenCalledTimes(2);
  });

  it("exports JSON when chosen and names the file when the server gives no name", async () => {
    const blob = new Blob(["[]"], { type: "application/json" });
    vi.mocked(downloadClaimLines).mockResolvedValue({ blob, fileName: null });
    render(<BillingScreen />);
    await screen.findByRole("button", { name: "Export 2 claim lines" });
    fireEvent.click(screen.getByRole("combobox", { name: "Format" }));
    fireEvent.click(screen.getByRole("option", { name: "JSON" }));
    fireEvent.click(screen.getByRole("button", { name: "Export 2 claim lines" }));
    await waitFor(() => expect(downloadClaimLines).toHaveBeenCalledWith("json"));
    await waitFor(() => expect(saveFile).toHaveBeenCalledWith(blob, "bodha-claim-lines.json"));
  });

  it("keeps the stored files on the exported tab and offers no second export there", async () => {
    search.value = "show=exported";
    vi.mocked(getBilling).mockResolvedValue(billing([{ ...ROW, exported_at: "2026-11-27T10:00:00Z" }]));
    render(<BillingScreen />);
    expect(await screen.findByRole("region", { name: "Export files" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /claim lines/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /again/ })).not.toBeInTheDocument();
  });
});
