import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Button } from "../Button";

function Saving({ onSave }: { onSave: () => void }) {
  const [pending, setPending] = useState(false);
  return (
    <Button
      variant="primary"
      pending={pending}
      onClick={() => {
        onSave();
        setPending(true);
      }}
    >
      Save
    </Button>
  );
}

function Submitting({ onSubmit, pending }: { onSubmit: () => void; pending: boolean }) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <input aria-label="Practice name" />
      <Button type="submit" pending={pending}>
        Create practice
      </Button>
    </form>
  );
}

describe("Button", () => {
  it("keeps focus while its action is pending and ignores further presses", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<Saving onSave={onSave} />);
    const save = screen.getByRole("button", { name: "Save" });
    save.focus();
    await user.keyboard("{Enter}");
    expect(save).toHaveFocus();
    expect(save).toHaveAttribute("aria-busy", "true");
    expect(save).toHaveAttribute("aria-disabled", "true");
    await user.keyboard("{Enter}");
    await user.click(save);
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it("does not submit its form again while pending", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<Submitting onSubmit={onSubmit} pending />);
    await user.type(screen.getByRole("textbox", { name: "Practice name" }), "Synthetic Clinic{Enter}");
    await user.click(screen.getByRole("button", { name: "Create practice" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("stays out of reach when it is disabled", () => {
    render(
      <Button disabled onClick={vi.fn()}>
        Save
      </Button>,
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });
});
