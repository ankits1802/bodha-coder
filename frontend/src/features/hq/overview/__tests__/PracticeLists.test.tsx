import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LAKESIDE } from "../../practice/__tests__/practiceFixtures";
import { AttentionList, BusiestTable } from "../PracticeLists";

const BLOCKED = { ...LAKESIDE, id: "p9", name: "Harbor Pediatrics", status: "blocked" as const, failed_24h: 2, last_failure: "PDF too large" };

describe("overview lists", () => {
  it("sends each item that needs attention to its practice page", () => {
    render(
      <AttentionList
        items={[
          { practice: BLOCKED, tone: "bad", reason: "2 notes could not be read: PDF too large" },
          { practice: BLOCKED, tone: "bad", reason: "Blocked" },
        ]}
      />,
    );
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
    for (const link of links) expect(link).toHaveAttribute("href", "/hq/practices/p9");
  });

  it("links the busiest practices to their pages", () => {
    render(<BusiestTable practices={[LAKESIDE]} />);
    expect(screen.getByRole("link", { name: "Lakeside Primary Care" })).toHaveAttribute("href", "/hq/practices/p1");
  });
});
