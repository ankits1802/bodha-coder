import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { StatCell, StatGrid } from "../StatGrid";

describe("StatCell", () => {
  it("shows a figure as plain text when it has no destination", () => {
    render(
      <StatGrid label="Summary">
        <StatCell label="Median time" value="4 min" />
        <StatCell label="People" value="12" href={null} />
      </StatGrid>,
    );
    const grid = screen.getByRole("region", { name: "Summary" });
    expect(within(grid).queryAllByRole("link")).toEqual([]);
    expect(within(grid).getByText("4 min")).toBeInTheDocument();
    expect(within(grid).getByText("People").parentElement).toHaveTextContent(/^People12$/);
  });

  it("opens its records as a real link named by the label and the figure", () => {
    render(
      <StatGrid label="Summary">
        <StatCell label="Organizations" value="3" href="/hq/organizations" />
      </StatGrid>,
    );
    const link = screen.getByRole("link", { name: "Organizations, 3" });
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("href", "/hq/organizations");
  });

  it("reads the note after the figure, so the name holds every word the cell shows", () => {
    render(
      <StatGrid label="Summary">
        <StatCell label="Waiting" value="12" note="3 reading now" href="/queue" />
      </StatGrid>,
    );
    expect(screen.getByRole("link", { name: "Waiting, 12, 3 reading now" })).toHaveAttribute("href", "/queue");
  });

  it("is reached with the keyboard and carries the hover and inset focus styles", async () => {
    const events = userEvent.setup();
    render(
      <StatGrid label="Summary">
        <StatCell label="Median time" value="4 min" />
        <StatCell label="Practices" value="8" href="/hq/practices?status=live" />
      </StatGrid>,
    );
    await events.tab();
    const link = screen.getByRole("link", { name: "Practices, 8" });
    expect(link).toHaveFocus();
    expect(link).toHaveClass("hover:bg-row-hover", "focus-visible:-outline-offset-2");
  });

  it("draws a lane dot beside the label and the larger figure in a large grid", () => {
    render(
      <StatGrid label="Waiting for review" size="lg">
        <StatCell label="Needs a coder" value="4" tone="warn" href="/queue?lane=coder" />
      </StatGrid>,
    );
    const link = screen.getByRole("link", { name: "Needs a coder, 4" });
    expect(within(link).getByText("4")).toHaveClass("text-stat-lg");
    expect(within(link).getByText("Needs a coder").querySelector("[aria-hidden='true']")).toHaveClass("bg-warn");
  });
});
