import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DecisionOverride } from "../components/DecisionOverride";
import { overrideProblem, reasonForKey, toOverride } from "../overrideReasons";

function renderPicker() {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(<DecisionOverride subject="Hypertension" onConfirm={onConfirm} onCancel={onCancel} />);
  return { onConfirm, onCancel };
}

describe("override reasons", () => {
  it("maps the number keys 1 to 6 to the reasons in order", () => {
    expect(["1", "2", "3", "4", "5", "6"].map(reasonForKey)).toEqual([
      "documentation",
      "payer_policy",
      "provider_answer",
      "coding_guideline",
      "clinical_context",
      "other",
    ]);
    expect(reasonForKey("7")).toBeNull();
    expect(reasonForKey("0")).toBeNull();
    expect(reasonForKey("a")).toBeNull();
  });

  it("needs a reason, a note for Other, and at most 500 characters", () => {
    expect(overrideProblem({ reason: null, note: "" })).toBe("choose");
    expect(overrideProblem({ reason: "other", note: "  " })).toBe("note");
    expect(overrideProblem({ reason: "payer_policy", note: "x".repeat(501) })).toBe("long");
    expect(toOverride({ reason: "payer_policy", note: "  " })).toEqual({ reason: "payer_policy", note: null });
    expect(toOverride({ reason: "other", note: " Contract 12 " })).toEqual({ reason: "other", note: "Contract 12" });
  });
});

describe("reason picker", () => {
  it("opens on the first reason, picks with a number key and confirms with Enter", async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderPicker();
    expect(screen.getByRole("group", { name: "Reason for Hypertension" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Documentation supports the billed code/ })).toHaveFocus();

    await user.keyboard("2");
    expect(screen.getByRole("radio", { name: /Payer policy/ })).toBeChecked();
    await user.keyboard("{Enter}");

    expect(onConfirm).toHaveBeenCalledWith({ reason: "payer_policy", note: null });
  });

  it("asks for a note before confirming Other", async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderPicker();

    await user.keyboard("6{Enter}");
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText("Write a short note for Other.")).toBeInTheDocument();

    await user.click(screen.getByRole("textbox", { name: "Note" }));
    await user.keyboard("Payer contract 12{Enter}");
    expect(onConfirm).toHaveBeenCalledWith({ reason: "other", note: "Payer contract 12" });
  });

  it("types digits into the note instead of switching reasons", async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderPicker();
    await user.keyboard("5");

    await user.click(screen.getByRole("textbox", { name: /Note/ }));
    await user.keyboard("Seen 3 times{Enter}");

    expect(onConfirm).toHaveBeenCalledWith({ reason: "clinical_context", note: "Seen 3 times" });
  });

  it("cancels the choice with Escape", async () => {
    const user = userEvent.setup();
    const { onConfirm, onCancel } = renderPicker();

    await user.keyboard("{Escape}");

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
