import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Button } from "../Button";
import { Dialog } from "../Dialog";

function Toggled() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Edit practice</Button>
      <Dialog open={open} onClose={() => setOpen(false)} title="Edit practice">
        <Button onClick={() => setOpen(false)}>Cancel</Button>
      </Dialog>
    </>
  );
}

function Mounted() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Add measure</Button>
      {open ? (
        <Dialog open onClose={() => setOpen(false)} title="New measure">
          <Button onClick={() => setOpen(false)}>Cancel</Button>
        </Dialog>
      ) : null}
    </>
  );
}

describe("Dialog", () => {
  it("returns focus to the button that opened it when it closes", async () => {
    const user = userEvent.setup();
    render(<Toggled />);
    await user.click(screen.getByRole("button", { name: "Edit practice" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("button", { name: "Edit practice" })).toHaveFocus();
  });

  it("returns focus to the button that opened it when its parent removes it", async () => {
    const user = userEvent.setup();
    render(<Mounted />);
    await user.click(screen.getByRole("button", { name: "Add measure" }));
    expect(screen.getByRole("dialog", { name: "New measure" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog", { name: "New measure" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add measure" })).toHaveFocus();
  });
});
