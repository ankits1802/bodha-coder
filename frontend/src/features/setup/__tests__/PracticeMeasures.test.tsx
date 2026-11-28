import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import { addPracticeMeasure, retirePracticeMeasure, saveMips } from "@/lib/api/practice";
import type { MipsOverview, PracticeMeasure } from "@/lib/api/types";
import { MipsEditor } from "../MipsEditor";

vi.mock("@/lib/api/practice", () => ({
  addPracticeMeasure: vi.fn(),
  changePracticeMeasure: vi.fn(),
  retirePracticeMeasure: vi.fn(),
  saveMips: vi.fn(),
}));

const FOOT: PracticeMeasure = {
  key: "P001",
  version: 1,
  name: "Diabetic foot follow-up",
  identifier: "QM-7",
  in_scope: "Adults with diabetes seen in the office.",
  out_of_scope: null,
  to_meet: "A monofilament foot exam result.",
  met_codes: [],
  not_met_codes: [],
  changed_at: "2026-11-28T10:00:00Z",
};

function overview(practice: PracticeMeasure[], measureIds: string[]): MipsOverview {
  return {
    standard: [{ id: "117", title: "Diabetes: Eye Exam" }],
    addable: [],
    practice,
    measure_ids: measureIds,
    uses_standard: measureIds.length === 0,
  };
}

describe("practice measures in the MIPS editor", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("lists the practice's own measures only in a custom list", async () => {
    render(<MipsEditor overview={overview([FOOT], [])} onReload={vi.fn()} />);
    expect(screen.queryByRole("group", { name: "Your measures" })).not.toBeInTheDocument();

    await userEvent.setup().click(screen.getByRole("radio", { name: "Custom list" }));

    const group = screen.getByRole("group", { name: "Your measures" });
    expect(within(group).getByRole("checkbox", { name: /Diabetic foot follow-up/ })).not.toBeChecked();
    expect(within(group).getByText("QM-7")).toBeInTheDocument();
  });

  it("adds a measure with Add your own, ticks it and saves it with the list", async () => {
    vi.mocked(addPracticeMeasure).mockResolvedValue(FOOT);
    vi.mocked(saveMips).mockResolvedValue({ measure_ids: ["117", "P001"] });
    const onReload = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<MipsEditor overview={overview([], ["117"])} onReload={onReload} />);

    await user.click(screen.getByRole("button", { name: "Add your own" }));
    const dialog = screen.getByRole("dialog", { name: "Add your own measure" });
    await user.type(within(dialog).getByRole("textbox", { name: "Name" }), FOOT.name);
    await user.type(within(dialog).getByRole("textbox", { name: "In scope when" }), FOOT.in_scope);
    await user.type(within(dialog).getByRole("textbox", { name: "Met when the note documents" }), FOOT.to_meet);
    await user.type(within(dialog).getByRole("textbox", { name: "Codes when met, optional" }), "g2178");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onReload).toHaveBeenCalledTimes(1));
    expect(addPracticeMeasure).toHaveBeenCalledWith(expect.objectContaining({ name: FOOT.name, met_codes: ["G2178"], identifier: null }));
    rerender(<MipsEditor overview={overview([FOOT], ["117"])} onReload={onReload} />);
    expect(screen.getByRole("checkbox", { name: /Diabetic foot follow-up/ })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Save measures" }));
    expect(saveMips).toHaveBeenCalledWith(["117", "P001"], ["117"]);
  });

  it("checks a measure in the browser before sending it", async () => {
    const user = userEvent.setup();
    render(<MipsEditor overview={overview([], ["117"])} onReload={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Add your own" }));
    const dialog = screen.getByRole("dialog", { name: "Add your own measure" });
    await user.type(within(dialog).getByRole("textbox", { name: "Your identifier, optional" }), "117");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(within(dialog).getByText("Add letters, for example QM-117")).toBeInTheDocument();
    expect(within(dialog).getByText("Use 3 to 80 characters")).toBeInTheDocument();
    expect(addPracticeMeasure).not.toHaveBeenCalled();
  });

  it("shows why a measure on the saved list cannot be retired", async () => {
    const message = "this measure is on the measure list; take it off and save the list before retiring it";
    vi.mocked(retirePracticeMeasure).mockRejectedValue(new ApiError(409, "conflict", message));
    const user = userEvent.setup();
    render(<MipsEditor overview={overview([FOOT], ["P001"])} onReload={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Retire Diabetic foot follow-up" }));
    await user.click(within(screen.getByRole("dialog", { name: "Retire Diabetic foot follow-up?" })).getByRole("button", { name: "Retire" }));

    expect(retirePracticeMeasure).toHaveBeenCalledWith("P001", 1);
    expect(await screen.findByText(/This measure is on the measure list/)).toBeInTheDocument();
  });
});
