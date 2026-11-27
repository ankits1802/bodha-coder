import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PayersPanel } from "../PayersPanel";

vi.mock("@/lib/api/practice", () => ({ removePayer: vi.fn(), addPayer: vi.fn(), changePayer: vi.fn() }));

describe("PayersPanel", () => {
  it("opens Add payer at once when the first steps link asked for it, and clears the request", () => {
    const onArrived = vi.fn();
    render(<PayersPanel payers={[]} addOnArrival onArrived={onArrived} onChanged={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Add payer" })).toBeInTheDocument();
    expect(onArrived).toHaveBeenCalledTimes(1);
  });

  it("stays closed on an ordinary visit", () => {
    const onArrived = vi.fn();
    render(<PayersPanel payers={[]} addOnArrival={false} onArrived={onArrived} onChanged={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(onArrived).not.toHaveBeenCalled();
  });
});
