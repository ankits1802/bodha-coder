import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HighlightedText } from "@/components/shared/HighlightedText";

describe("HighlightedText", () => {
  it("renders markup in the note as plain text", () => {
    const text = "<script>alert(1)</script> CKD, stable";
    const { container } = render(<HighlightedText text={text} marks={[{ quote: "CKD, stable", tone: "warn" }]} />);

    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toBe(text);
  });

  it("wraps only the exact quote in a highlight with its tone", () => {
    const { container } = render(
      <HighlightedText text="Hypertension, rule out neuropathy" marks={[{ quote: "rule out neuropathy", tone: "bad" }]} />,
    );

    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0]?.textContent).toBe("rule out neuropathy");
    expect(marks[0]?.className).toContain("hl-bad");
  });

  it("tells screen readers where each highlight starts and ends when given labels", () => {
    const { container } = render(
      <HighlightedText
        text="Afebrile. Lungs clear."
        marks={[{ quote: "Afebrile", tone: "ok" }]}
        labels={{ start: "Evidence:", end: "End of evidence" }}
      />,
    );

    const mark = container.querySelector("mark");
    expect(mark?.textContent).toBe("Evidence: Afebrile End of evidence");
    expect([...(mark?.querySelectorAll(".sr-only") ?? [])].map((label) => label.textContent)).toEqual(["Evidence: ", " End of evidence"]);
    expect(container.textContent).toBe("Evidence: Afebrile End of evidence. Lungs clear.");
  });

  it("treats a quote containing markup as literal text", () => {
    const { container } = render(<HighlightedText text="Plan: <b>add amlodipine</b>" marks={[{ quote: "<b>add amlodipine</b>", tone: "ok" }]} />);

    expect(container.querySelector("b")).toBeNull();
    expect(container.querySelector("mark")?.textContent).toBe("<b>add amlodipine</b>");
  });
});
