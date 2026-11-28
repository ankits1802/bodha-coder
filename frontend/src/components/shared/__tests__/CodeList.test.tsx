import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CodeList } from "../CodeList";

describe("CodeList", () => {
  it("shows a readable dash when there are no codes", () => {
    render(<CodeList codes={[]} />);
    const dash = screen.getByText("—");
    expect(dash).toHaveClass("text-tertiary");
    expect(dash).not.toHaveClass("text-quaternary");
  });
});
