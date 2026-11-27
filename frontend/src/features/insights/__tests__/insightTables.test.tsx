import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EstimateTable } from "../components/EstimateTable";
import { PeopleTable } from "../components/PeopleTable";

describe("EstimateTable", () => {
  it("lists each provider's estimated Medicare national difference with its sign", () => {
    render(
      <EstimateTable
        estimates={{
          notes: 3,
          difference: -16.36,
          providers: [
            { provider_name: "Elena Varga", notes: 2, difference: -16.36 },
            { provider_name: "Omar Haddad", notes: 1, difference: 40.42 },
          ],
        }}
      />,
    );

    const table = screen.getByRole("table", { name: "Estimated Medicare national difference by provider" });
    const rows = within(table).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Elena Varga2-$16.36");
    expect(rows[2]).toHaveTextContent("Omar Haddad1+$40.42");
  });

  it("says so when no approved note has an estimate", () => {
    render(<EstimateTable estimates={{ notes: 0, difference: 0, providers: [] }} />);

    expect(screen.getByText("No approved notes with an estimate in this period")).toBeInTheDocument();
  });
});

describe("PeopleTable", () => {
  it("shows approvals, the median wait and the share changed in review", () => {
    render(
      <PeopleTable
        people={[
          { id: "u1", name: "Ana Ruiz", approved: 4, median_minutes: 7.5, changed: 1 },
          { id: "u2", name: "Ben Okafor", approved: 2, median_minutes: 90, changed: 0 },
          { id: "u3", name: "Chen Li", approved: 1, median_minutes: null, changed: 1 },
        ]}
      />,
    );

    const rows = within(screen.getByRole("table", { name: "Approvals by person in this period" })).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Ana Ruiz47.5 min25%");
    expect(rows[2]).toHaveTextContent("Ben Okafor21.5 h0%");
    expect(rows[3]).toHaveTextContent("Chen Li1—100%");
  });
});
