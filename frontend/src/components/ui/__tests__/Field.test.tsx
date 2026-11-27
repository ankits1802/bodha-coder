import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Field } from "../Field";
import { Input } from "../Input";

describe("Field", () => {
  it("reads an optional field's label with a pause before the word optional", () => {
    render(
      <Field label="NPI" optional="optional">
        {(control) => <Input {...control} />}
      </Field>,
    );
    expect(screen.getByRole("textbox")).toHaveAccessibleName("NPI, optional");
  });

  it("names a required field by its label alone and ties its error to the control", () => {
    render(
      <Field label="Name" error="Enter a name">
        {(control) => <Input {...control} />}
      </Field>,
    );
    const input = screen.getByRole("textbox", { name: "Name" });
    expect(input).toHaveAccessibleDescription("Enter a name");
    expect(input).toHaveAttribute("aria-invalid", "true");
  });
});
