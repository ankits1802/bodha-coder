import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { PasswordInput } from "../PasswordInput";

function renderField() {
  render(
    <>
      <label htmlFor="password">Password</label>
      <PasswordInput id="password" autoComplete="new-password" defaultValue="" />
    </>,
  );
  return screen.getByLabelText("Password");
}

describe("PasswordInput", () => {
  it("shows and hides the password without changing its value or autocomplete", async () => {
    const user = userEvent.setup();
    const field = renderField();
    await user.type(field, "correct-horse-staple");

    const show = screen.getByRole("button", { name: "Show password" });
    expect(field).toHaveAttribute("type", "password");
    expect(show).toHaveAttribute("aria-pressed", "false");
    expect(show).toHaveAttribute("type", "button");

    await user.click(show);
    const hide = screen.getByRole("button", { name: "Hide password" });
    expect(field).toHaveAttribute("type", "text");
    expect(hide).toHaveAttribute("aria-pressed", "true");
    expect(field).toHaveValue("correct-horse-staple");
    expect(field).toHaveAttribute("autocomplete", "new-password");
    expect(field).toHaveFocus();

    await user.click(hide);
    expect(field).toHaveAttribute("type", "password");
    expect(field).toHaveValue("correct-horse-staple");
  });

  it("is reachable by keyboard and returns focus to the field after toggling", async () => {
    const user = userEvent.setup();
    const field = renderField();
    await user.click(field);
    await user.tab();
    expect(screen.getByRole("button", { name: "Show password" })).toHaveFocus();

    await user.keyboard("{Enter}");
    expect(field).toHaveAttribute("type", "text");
    expect(field).toHaveFocus();
  });
});
