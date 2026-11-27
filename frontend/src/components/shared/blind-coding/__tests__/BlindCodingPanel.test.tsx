import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { BlindItem } from "@/lib/api/types";
import { BlindCodingPanel } from "../BlindCodingPanel";

const NOTE = "Follow-up of diabetes and blood pressure. A1c 8.4.";

function leakyItem(): BlindItem {
  const item = {
    id: "item-1",
    position: 2,
    texts: [
      { revision: 1, source: "document", text: NOTE },
      { revision: 2, source: "addendum", text: "Stage 3a chronic kidney disease." },
    ],
    findings: [{ title: "Billed too high", code_before: "99215", code_after: "99214" }],
    claim: ["99214", "E11.65"],
    bodha: { em: "99214", icd: ["E11.65", "I12.9"], modifiers: [] },
  };
  return item as unknown as BlindItem;
}

function renderPanel(onSubmit = vi.fn()) {
  render(
    <BlindCodingPanel
      item={leakyItem()}
      total={30}
      pending={false}
      error={null}
      pdfPending={false}
      onSubmit={onSubmit}
      onOpenPdf={vi.fn()}
    />,
  );
  return onSubmit;
}

describe("BlindCodingPanel", () => {
  it("shows the note text and the PDF button, never Bodha's suggestions or the claim", () => {
    renderPanel();

    expect(screen.getByText("Note 2 of 30")).toBeInTheDocument();
    expect(screen.getByText(NOTE)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Addendum 2" })).toHaveTextContent("Stage 3a chronic kidney disease.");
    expect(screen.getByRole("button", { name: "Open PDF" })).toBeInTheDocument();
    for (const leaked of [/Billed too high/, /99214/, /99215/, /E11\.65/, /I12\.9/]) {
      expect(screen.queryByText(leaked)).not.toBeInTheDocument();
    }
    expect(document.body.textContent).not.toMatch(/99214|E11\.65|Billed too high/);
  });

  it("takes the whole answer from the keyboard and submits it with Enter", async () => {
    const user = userEvent.setup();
    const onSubmit = renderPanel();

    await user.type(screen.getByRole("textbox", { name: "E/M code" }), "99214");
    await user.tab();
    await user.keyboard("e11.65, i12.9 E11.65");
    await user.tab();
    await user.keyboard("25{Enter}");

    expect(onSubmit).toHaveBeenCalledWith({ em: "99214", icd: ["E11.65", "I12.9"], modifiers: ["25"] });
  });

  it("explains a missing or malformed code beside its field and does not submit", async () => {
    const user = userEvent.setup();
    const onSubmit = renderPanel();

    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(screen.getByText("Enter the E/M code or a diagnosis")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: "E/M code" }), "9921");
    await user.type(screen.getByRole("textbox", { name: /Modifiers/ }), "2{Enter}");
    expect(screen.getByText("Enter a five-digit E/M code")).toBeInTheDocument();
    expect(screen.getByText("Not modifiers: 2")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
