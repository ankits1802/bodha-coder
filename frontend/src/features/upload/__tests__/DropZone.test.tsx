import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DropZone } from "../components/FilePicker";

function pdf(name: string): File {
  return new File(["%PDF-1.7"], name, { type: "application/pdf" });
}

describe("DropZone", () => {
  it("shows where to drop and a primary way to choose files when nothing is added yet", async () => {
    const onFiles = vi.fn();
    const { container } = render(<DropZone onFiles={onFiles} />);
    const zone = screen.getByRole("region", { name: "Files" });
    expect(within(zone).getByText("Drop PDF notes here")).toBeInTheDocument();
    const choose = within(zone).getByRole("button", { name: "Choose files" });
    expect(choose.className).toContain("bg-primary");
    const input = container.querySelector("input[type=file]");
    if (!(input instanceof HTMLInputElement)) throw new Error("no file input");
    await userEvent.setup().upload(input, [pdf("a.pdf"), pdf("b.pdf")]);
    expect(onFiles).toHaveBeenCalledWith([expect.objectContaining({ name: "a.pdf" }), expect.objectContaining({ name: "b.pdf" })]);
  });

  it("stays below the files as a smaller place to add more", () => {
    render(<DropZone onFiles={vi.fn()} compact />);
    const zone = screen.getByRole("region", { name: "Add more files" });
    expect(within(zone).getByText("Drop more PDF notes here")).toBeInTheDocument();
    expect(within(zone).getByRole("button", { name: "Add files" }).className).not.toContain("bg-primary");
  });
});
