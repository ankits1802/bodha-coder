import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { saveBilledCodes, saveDecisions } from "@/lib/api/notes";
import type { NoteDetail } from "@/lib/api/types";
import { ReviewPanel } from "../components/ReviewPanel";
import { withChoices } from "../decisionFlow";
import { reviewPermissions } from "../permissions";
import { useDecisions } from "../useDecisions";
import { useOverridePrompt } from "../useOverridePrompt";
import type { ReviewActions } from "../useReviewActions";
import { finding, noteDetail } from "./fixtures";

const navigation = vi.hoisted(() => ({ search: "", replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/notes/note-1",
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));
vi.mock("@/lib/api/notes", () => ({ saveDecisions: vi.fn(), saveBilledCodes: vi.fn() }));

const EM = finding({ kind: "em", key: "em", action: "lower", code_before: "99215", code_after: "99213", choice: "accept", allowed: ["accept", "keep"], departing_choices: ["keep"], amount_change: -96.4 });
const QUERY = finding({ kind: "cdi_query", key: "cdiq-1", action: "ask", code_before: null, choice: "ask", allowed: ["ask", "skip"], title: "Stage of the kidney disease" });
const SUSPECTED = finding({ key: "hcc:18", action: "add", code_before: null, code_after: "E11.9", choice: "skip", allowed: ["add", "skip"], title: "Diabetes" });
const SUPPORTED = [finding({}), finding({ key: "dx:E78.5", code_before: "E78.5", title: "Hyperlipidemia" })];
const BILLED = { kind: "billed", revision: 1, codes: [{ code: "99215", type: "CPT", modifiers: [] }], reason: "upload", by: null, role: null, at: "2026-11-27T09:00:00Z", override_reason: null, override_note: null };
const ACTIONS = { remind: vi.fn(), cancelRequest: vi.fn(), remindPending: false, cancelPending: false, remindError: null } as unknown as ReviewActions;

function Harness({ initial }: { initial: NoteDetail }) {
  const [detail, setDetail] = useState(initial);
  const decisions = useDecisions(detail, setDetail);
  const prompt = useOverridePrompt(decisions);
  return (
    <ReviewPanel
      detail={detail}
      permissions={reviewPermissions("coder", detail)}
      actions={ACTIONS}
      decisions={decisions}
      prompt={prompt}
      onReplace={setDetail}
      onAsk={null}
    />
  );
}

function renderPanel(findings = [EM, QUERY, SUSPECTED, ...SUPPORTED]) {
  const detail = noteDetail(findings, { history: { ...noteDetail([]).history, code_sets: [BILLED] } });
  vi.mocked(saveDecisions).mockImplementation((_, choices) => Promise.resolve(withChoices(detail, choices)));
  render(<Harness initial={detail} />);
  return userEvent.setup();
}

function currentTitle(): string | null {
  return document.querySelector("[aria-current='true']")?.textContent ?? null;
}

describe("the findings list from the keyboard", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    navigation.search = "";
    vi.stubGlobal("requestAnimationFrame", () => 0);
  });

  it("moves with J, K and the arrows and decides the finding that holds the bar wherever it sits", async () => {
    const user = renderPanel();
    expect(currentTitle()).toContain("99215");
    await user.keyboard("j");
    expect(currentTitle()).toContain("Stage of the kidney disease");
    await user.keyboard("n");
    expect(saveDecisions).toHaveBeenCalledWith("note-1", { "cdiq-1": "skip" }, {});
    expect(currentTitle()).toContain("Diabetes");
    await user.keyboard("y");
    expect(saveDecisions).toHaveBeenLastCalledWith("note-1", { "hcc:18": "add" }, {});
    expect(currentTitle()).toBeNull();
    await user.keyboard("k");
    expect(currentTitle()).toContain("Diabetes");
    await user.keyboard("{ArrowUp}");
    expect(currentTitle()).toContain("Stage of the kidney disease");
  });

  it("asks for a reason instead of saving when N turns down a proposed change", async () => {
    const user = renderPanel();
    await user.keyboard("n");
    expect(saveDecisions).not.toHaveBeenCalled();
    expect(screen.getByRole("group", { name: /Reason for/ })).toBeInTheDocument();
  });

  it("accepts every supported finding at once with Shift Y and asks for no reason", async () => {
    const user = renderPanel();
    expect(screen.getByRole("button", { name: "2 supported" })).toHaveAttribute("aria-expanded", "false");
    await user.keyboard("{Shift>}Y{/Shift}");
    expect(saveDecisions).toHaveBeenCalledWith("note-1", { "dx:I10": "keep", "dx:E78.5": "keep" }, {});
    expect(await screen.findByText("Accepted")).toBeInTheDocument();
  });

  it("edits the billed codes with E and saves with Enter once a reason is chosen", async () => {
    vi.mocked(saveBilledCodes).mockResolvedValue(noteDetail([]));
    const user = renderPanel();
    await user.keyboard("e");
    const field = screen.getByRole("textbox", { name: "Billed codes" });
    expect(field).toHaveFocus();
    await user.keyboard(", 99417{Enter}");
    expect(saveBilledCodes).not.toHaveBeenCalled();
    expect(screen.getByRole("radio", { name: /Documentation supports the billed code/ })).toHaveFocus();
    await user.keyboard("1{Enter}");
    expect(saveBilledCodes).toHaveBeenCalledWith("note-1", "99215, 99417", { reason: "documentation", note: null });
  });

  it("asks for a fresh decision on a finding compliance returned, even with the same choice", async () => {
    const user = renderPanel([{ ...EM, decide_again: true }]);
    const row = screen.getByText("Decide again").closest("li");
    expect(row && within(row).queryByRole("radio", { checked: true })).toBeNull();
    await user.keyboard("y");
    expect(saveDecisions).toHaveBeenCalledWith("note-1", { em: "accept" }, {});
  });
});

describe("filters and History", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("requestAnimationFrame", () => 0);
  });

  it("keeps the filter in the address and opens an old tab link on the nearest filter", async () => {
    navigation.search = "tab=questions";
    const user = renderPanel();
    expect(screen.getByRole("radio", { name: /Questions/ })).toHaveAttribute("aria-checked", "true");
    expect(screen.queryByText("Diabetes")).not.toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /Risk/ }));
    expect(navigation.replace).toHaveBeenCalledWith("/notes/note-1?filter=risk", { scroll: false });
  });

  it("opens History in a drawer from the button and from the old History tab", async () => {
    navigation.search = "tab=history";
    renderPanel();
    expect(screen.getByRole("dialog", { name: "History" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Returned to the coder" })).toBeInTheDocument();
  });
});
