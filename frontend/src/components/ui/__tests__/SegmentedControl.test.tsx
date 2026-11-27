import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SegmentedControl } from "../SegmentedControl";

const SEGMENTS = [
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
];

describe("SegmentedControl", () => {
  it("lets Tab reach the chosen segment only", () => {
    render(<SegmentedControl label="Range" value="month" segments={SEGMENTS} onChange={() => undefined} />);
    expect(screen.getByRole("radio", { name: "Month" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("radio", { name: "Week" })).toHaveAttribute("tabindex", "-1");
  });

  it("checks nothing when no segment is chosen and still lets Tab reach the first", () => {
    render(<SegmentedControl label="Range" value={null} segments={SEGMENTS} onChange={() => undefined} />);
    expect(screen.getAllByRole("radio").map((radio) => radio.getAttribute("aria-checked"))).toEqual(["false", "false"]);
    expect(screen.getByRole("radio", { name: "Week" })).toHaveAttribute("tabindex", "0");
  });
});
