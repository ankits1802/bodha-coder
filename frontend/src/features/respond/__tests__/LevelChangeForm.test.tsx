import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LevelChangeForm } from "../LevelChangeForm";

const WORDING = "I reviewed the billed and approved visit levels and the evidence shown";
const CHANGE = {
  billed: "99215",
  approved: "99214",
  shown: "Visit of 25 Nov 2026\nBilled level: 99215\nApproved level: 99214\nEvidence from the note:\n“increase metformin”",
};

function renderForm() {
  const onSend = vi.fn();
  render(<LevelChangeForm change={CHANGE} attestation={WORDING} pending={false} error={null} onSend={onSend} />);
  return { onSend, send: () => screen.getByRole("button", { name: "Send" }) };
}

describe("visit level confirmation", () => {
  it("shows what the provider is asked about and confirms with the attestation", async () => {
    const user = userEvent.setup();
    const form = renderForm();
    expect(screen.getByText(/Approved level: 99214/)).toBeInTheDocument();
    expect(form.send()).toBeDisabled();

    await user.click(screen.getByRole("radio", { name: "Confirm" }));
    expect(form.send()).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: WORDING }));
    await user.click(form.send());

    expect(form.onSend).toHaveBeenCalledWith({ answer: "confirm", comment: null, confirmed: true, attestation: WORDING });
  });

  it("needs a comment to disagree", async () => {
    const user = userEvent.setup();
    const form = renderForm();
    await user.click(screen.getByRole("radio", { name: "Disagree" }));
    await user.click(screen.getByRole("checkbox", { name: WORDING }));
    expect(form.send()).toBeDisabled();
    expect(screen.getByText("Say why you disagree.")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: "Comment" }), "Time supports 99215.");
    await user.click(form.send());

    expect(form.onSend).toHaveBeenCalledWith({
      answer: "disagree",
      comment: "Time supports 99215.",
      confirmed: true,
      attestation: WORDING,
    });
  });
});
