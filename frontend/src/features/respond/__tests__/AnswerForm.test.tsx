import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AddendumQuestion } from "@/lib/api/types";
import { AnswerForm } from "../AnswerForm";
import { SAVED_SIGNATURE } from "./signatureFixture";

const questions: AddendumQuestion[] = [
  {
    key: "cdiq-1",
    text: "What stage is the chronic kidney disease?",
    context: ["CKD, stable"],
    options: ["Stage 3a", "Stage 3b", "Other"],
  },
  {
    key: "cdiq-2",
    text: "Is the kidney disease due to the diabetes?",
    context: [],
    options: ["Yes", "No", "Other"],
  },
];

function renderForm(onSign = vi.fn()) {
  render(
    <AnswerForm
      questions={questions}
      providerName="Elena Varga, MD"
      attestation="This is clinically accurate"
      pending={false}
      error={null}
      remembered={SAVED_SIGNATURE}
      onSign={onSign}
    />,
  );
  return {
    onSign,
    stageGroup: () => screen.getByRole("group", { name: /What stage is the chronic kidney disease/ }),
    causeGroup: () => screen.getByRole("group", { name: /Is the kidney disease due to the diabetes/ }),
    signButton: () => screen.getByRole("button", { name: "Sign and add to note" }),
    confirm: () => screen.getByRole("checkbox", { name: "This is clinically accurate" }),
  };
}

describe("provider answer form", () => {
  it("keeps signing disabled until every question is answered and the answers are confirmed", async () => {
    const user = userEvent.setup();
    const form = renderForm();
    expect(form.signButton()).toBeDisabled();

    await user.click(within(form.stageGroup()).getByRole("radio", { name: "Stage 3b" }));
    await user.click(form.confirm());
    expect(form.signButton()).toBeDisabled();

    await user.click(within(form.causeGroup()).getByRole("radio", { name: "Yes" }));
    expect(form.signButton()).toBeEnabled();

    await user.click(form.confirm());
    expect(form.signButton()).toBeDisabled();
  });

  it("requires a comment when Other is chosen", async () => {
    const user = userEvent.setup();
    const form = renderForm();
    await user.click(within(form.stageGroup()).getByRole("radio", { name: "Other" }));
    await user.click(within(form.causeGroup()).getByRole("radio", { name: "No" }));
    await user.click(form.confirm());

    expect(screen.getByText("Write your answer for Other.")).toBeInTheDocument();
    expect(form.signButton()).toBeDisabled();

    await user.type(within(form.stageGroup()).getByRole("textbox", { name: "Your answer" }), "Stage 4");
    expect(screen.queryByText("Write your answer for Other.")).not.toBeInTheDocument();
    expect(form.signButton()).toBeEnabled();
  });

  it("previews the addendum and signs with the chosen answers", async () => {
    const user = userEvent.setup();
    const form = renderForm();
    await user.click(within(form.stageGroup()).getByRole("radio", { name: "Other" }));
    await user.type(within(form.stageGroup()).getByRole("textbox", { name: "Your answer" }), "Stage 4");
    await user.click(within(form.causeGroup()).getByRole("radio", { name: "Yes" }));

    const preview = screen.getByRole("region", { name: "Addendum preview" });
    expect(within(preview).getByText(/^Addendum by Elena Varga, MD, \d{2} [A-Z][a-z]{2} \d{4}\.$/)).toBeInTheDocument();
    expect(within(preview).getByText("What stage is the chronic kidney disease? Stage 4.")).toBeInTheDocument();
    expect(within(preview).getByText("Is the kidney disease due to the diabetes? Yes.")).toBeInTheDocument();

    await user.click(form.confirm());
    await user.click(form.signButton());
    expect(form.onSign).toHaveBeenCalledWith(
      [
        { key: "cdiq-1", choice: "Other", comment: "Stage 4" },
        { key: "cdiq-2", choice: "Yes", comment: null },
      ],
      expect.objectContaining({ useSaved: true, remembered: SAVED_SIGNATURE }),
    );
  });
});
