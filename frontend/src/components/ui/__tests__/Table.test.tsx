import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Table, Td, Th, Tr } from "../Table";

function widths(scroll: number, client: number): void {
  vi.spyOn(Element.prototype, "scrollWidth", "get").mockReturnValue(scroll);
  vi.spyOn(Element.prototype, "clientWidth", "get").mockReturnValue(client);
}

function Practices() {
  return (
    <Table label="Practices in the organization">
      <thead>
        <Tr>
          <Th>Practice</Th>
        </Tr>
      </thead>
      <tbody>
        <Tr>
          <Td>Synthetic Family Clinic</Td>
        </Tr>
      </tbody>
    </Table>
  );
}

describe("Table", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lets the keyboard reach a table wider than its column so it can be scrolled", () => {
    widths(820, 358);
    render(<Practices />);
    const scroller = screen.getByRole("region", { name: "Practices in the organization" });
    expect(scroller).toHaveAttribute("tabindex", "0");
    expect(scroller).toContainElement(screen.getByRole("table", { name: "Practices in the organization" }));
  });

  it("adds no stop for the keyboard when the table fits", () => {
    widths(640, 640);
    render(<Practices />);
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Practices in the organization" }).parentElement).not.toHaveAttribute("tabindex");
  });
});
