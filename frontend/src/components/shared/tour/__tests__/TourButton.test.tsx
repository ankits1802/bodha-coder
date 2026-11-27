import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { closeOverlay, useOpenOverlay } from "../../overlays";
import { TourButton } from "../TourButton";

function OpenOverlay() {
  return <output>{useOpenOverlay() ?? "none"}</output>;
}

describe("TourButton", () => {
  afterEach(() => closeOverlay());

  it("starts the tour from the account menu and marks itself as the replay step's target", async () => {
    render(
      <>
        <TourButton user={CODER} collapsed={false} />
        <OpenOverlay />
      </>,
    );
    const button = screen.getByRole("button", { name: "Take the tour" });
    expect(button).toHaveAttribute("data-tour", "tour");
    await userEvent.setup().click(button);
    expect(screen.getByRole("status")).toHaveTextContent("tour");
  });

  it("keeps its name as an icon in the collapsed sidebar", () => {
    render(<TourButton user={CODER} collapsed />);
    expect(screen.getByRole("button", { name: "Take the tour" })).toHaveAttribute("title", "Take the tour");
  });

  it("is not offered to a billing-only account", () => {
    render(<TourButton user={{ ...CODER, role: "admin", billing_only: true }} collapsed={false} />);
    expect(screen.queryByRole("button", { name: "Take the tour" })).not.toBeInTheDocument();
  });
});
