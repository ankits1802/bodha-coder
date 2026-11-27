import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { LANDING_TEXT } from "../strings";
import { Estimator } from "../worth/Estimator";

const fields = LANDING_TEXT.worth.fields;

describe("Estimator", () => {
  it("shows the defaults: $2,000.00 recovered and $1,200.00 exposure a month", () => {
    render(<Estimator />);
    expect(screen.getByText("$2,000.00")).toBeInTheDocument();
    expect(screen.getByText("$1,200.00")).toBeInTheDocument();
    expect(screen.getByText("$24,000.00 a year")).toBeInTheDocument();
    expect(screen.getByText("$14,400.00 a year")).toBeInTheDocument();
    expect(screen.getByText(LANDING_TEXT.worth.note)).toBeInTheDocument();
  });

  it("recomputes from a typed number of visits", async () => {
    const user = userEvent.setup();
    render(<Estimator />);
    const visits = screen.getByRole("spinbutton", { name: fields.visits });
    await user.clear(visits);
    await user.type(visits, "2000");
    expect(screen.getByText("$4,000.00")).toBeInTheDocument();
    expect(screen.getByText("$2,400.00")).toBeInTheDocument();
  });

  it("moves the number field with its slider", () => {
    render(<Estimator />);
    fireEvent.change(screen.getByRole("slider", { name: fields.difference }), { target: { value: "60" } });
    expect(screen.getByRole("spinbutton", { name: fields.difference })).toHaveValue(60);
    expect(screen.getByText("$3,000.00")).toBeInTheDocument();
    expect(screen.getByText("$1,800.00")).toBeInTheDocument();
  });

  it("names the range beside a value outside it and shows no estimate", async () => {
    const user = userEvent.setup();
    render(<Estimator />);
    const low = screen.getByRole("spinbutton", { name: fields.lowPercent });
    await user.clear(low);
    await user.type(low, "45");
    expect(low).toHaveAttribute("aria-invalid", "true");
    expect(low).toHaveAccessibleDescription("Enter 0% to 30%");
    expect(screen.getAllByText("—")).toHaveLength(2);
  });
});
