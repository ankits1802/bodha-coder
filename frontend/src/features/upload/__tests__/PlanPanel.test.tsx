import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Provider } from "@/lib/api/types";
import { PlanPanel } from "../components/PlanPanel";
import { newEntry, type References } from "../uploadEntries";

const REFERENCES: References = {
  providers: [{ id: "prov-1", name: "Elena Varga", credential: "MD", payer: null } as Provider],
  places: [{ code: "11", name: "Office" }],
  payers: [{ id: "payer-medicare", name: "Medicare Part B", plan_type: "medicare" }],
};

function entries() {
  return [newEntry(new File(["%PDF-1.7"], "a.pdf", { type: "application/pdf" }), "1")];
}

describe("PlanPanel", () => {
  it("offers the payer for all files as a recommended field and passes the choice on", async () => {
    const onPayer = vi.fn();
    const user = userEvent.setup();
    render(
      <PlanPanel entries={entries()} references={REFERENCES} visitType="Established patient" onPlace={vi.fn()} onPayer={onPayer} onVisitType={vi.fn()} />,
    );

    const payer = screen.getByRole("combobox", { name: "Payer for all, Recommended" });
    expect(payer).toHaveTextContent("None");
    await user.click(payer);
    await user.click(screen.getByRole("option", { name: "Medicare Part B" }));

    expect(onPayer).toHaveBeenCalledWith("payer-medicare");
  });

  it("shows no payer field while the practice lists no payers", () => {
    render(
      <PlanPanel
        entries={entries()}
        references={{ ...REFERENCES, payers: [] }}
        visitType="Established patient"
        onPlace={vi.fn()}
        onPayer={vi.fn()}
        onVisitType={vi.fn()}
      />,
    );
    expect(screen.queryByRole("combobox", { name: /Payer for all/ })).not.toBeInTheDocument();
  });
});
