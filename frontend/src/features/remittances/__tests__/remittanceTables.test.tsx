import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import type { RemittanceLine, RemittanceListItem } from "@/lib/api/types";
import { RemittanceFiles } from "../components/RemittanceFiles";
import { RemittanceLines } from "../components/RemittanceLines";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function line(overrides: Partial<RemittanceLine>): RemittanceLine {
  return {
    id: "l1",
    note_id: null,
    claim_ref: "ACCT1",
    patient_name: null,
    service_date: null,
    billed_code: null,
    paid_code: null,
    billed_amount: null,
    paid_amount: null,
    adjustments: [],
    status: "unmatched",
    appeal_by: null,
    ...overrides,
  };
}

const LINES: RemittanceLine[] = [
  line({
    id: "l1",
    note_id: "n1",
    patient_name: "Marisol Reyes",
    service_date: "2026-11-20",
    billed_code: "99215",
    paid_code: "99214",
    billed_amount: 20000,
    paid_amount: 9000,
    status: "downcoded",
    appeal_by: "2027-03-24",
  }),
  line({
    id: "l2",
    note_id: "n2",
    patient_name: "James Okafor",
    service_date: "2026-11-21",
    billed_code: "99213",
    paid_code: "99213",
    billed_amount: 12000,
    paid_amount: 8500,
    status: "paid_as_billed",
  }),
  line({
    id: "l3",
    patient_name: "Jane Doe",
    service_date: "2026-11-23",
    billed_code: "99212",
    paid_code: "99212",
    billed_amount: 9000,
    paid_amount: 0,
    status: "unmatched",
    appeal_by: "2027-05-23",
  }),
];

describe("RemittanceLines", () => {
  it("shows each line's codes, amounts, status word and appeal date", () => {
    render(<RemittanceLines lines={LINES} onDraft={vi.fn()} />);

    const rows = within(screen.getByRole("table", { name: "Remittance lines" })).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Marisol Reyes20 Nov99215 → 99214$200.00 · $90.00Downcoded24 Mar 2027Draft appeal");
    expect(rows[2]).toHaveTextContent("James Okafor21 Nov99213$120.00 · $85.00Paid as billed—");
    expect(rows[3]).toHaveTextContent("Jane Doe23 Nov99212$90.00 · $0.00Unmatched23 May 2027Draft appeal");
    expect(within(rows[1]!).getByRole("link", { name: "Marisol Reyes" })).toHaveAttribute("href", "/notes/n1");
    expect(within(rows[2]!).queryByRole("button", { name: "Draft appeal" })).not.toBeInTheDocument();
    expect(within(rows[3]!).queryByRole("link")).not.toBeInTheDocument();
  });

  it("opens the appeal for the line whose button was pressed", async () => {
    const onDraft = vi.fn();
    render(<RemittanceLines lines={LINES} onDraft={onDraft} />);

    const rows = within(screen.getByRole("table", { name: "Remittance lines" })).getAllByRole("row");
    await userEvent.click(within(rows[3]!).getByRole("button", { name: "Draft appeal" }));

    expect(onDraft).toHaveBeenCalledWith("l3");
  });
});

describe("RemittanceFiles", () => {
  const file: RemittanceListItem = {
    id: "r1",
    file_name: "acme-era.835",
    payer: "ACME HEALTH PLAN",
    paid_on: "2026-11-24",
    uploaded_by: "Practice Admin",
    uploaded_at: "2026-11-25T10:00:00Z",
    counts: { paid_as_billed: 2, downcoded: 1, unmatched: 1 },
    next_appeal_by: "2027-03-24",
  };

  it("lists each file with its line counts by status and selects it", async () => {
    const onSelect = vi.fn();
    render(<RemittanceFiles files={[file]} selectedId={null} onSelect={onSelect} />);

    const row = within(screen.getByRole("table", { name: "Remittance files" })).getAllByRole("row")[1]!;
    expect(row).toHaveTextContent("acme-era.835ACME HEALTH PLAN24 Nov 20261 Downcoded1 Unmatched2 Paid as billed24 Mar 2027");
    await userEvent.click(within(row).getByRole("button", { name: "acme-era.835" }));
    expect(onSelect).toHaveBeenCalledWith("r1");
  });
});
