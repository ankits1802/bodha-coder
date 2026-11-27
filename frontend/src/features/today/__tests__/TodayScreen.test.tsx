import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { planStatus } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { CODER, ROW } from "@/features/queue/__tests__/fixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { refreshSession } from "@/lib/api/client";
import { getPlanStatus } from "@/lib/api/plan";
import { dismissFirstRun, getSetup, saveChecks, saveSecurity } from "@/lib/api/practice";
import { getTraining } from "@/lib/api/quality";
import { getTeam } from "@/lib/api/team";
import type { Role, TodaySummary, TrainingOverview } from "@/lib/api/types";
import { getToday } from "@/lib/api/work";
import { clearSession, setSession } from "@/lib/session/store";
import { RECOMMENDED_SECURITY } from "../checklist/checklistModel";
import { TodayScreen } from "../TodayScreen";
import { setupWith, teamOf } from "./firstRunFixtures";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => "/today" }));
vi.mock("@/lib/api/work", () => ({ getToday: vi.fn() }));
vi.mock("@/lib/api/practice", () => ({ getSetup: vi.fn(), saveChecks: vi.fn(), saveSecurity: vi.fn(), dismissFirstRun: vi.fn() }));
vi.mock("@/lib/api/team", () => ({ getTeam: vi.fn(), inviteMember: vi.fn() }));
vi.mock("@/lib/api/plan", () => ({ getPlanStatus: vi.fn() }));
vi.mock("@/lib/api/quality", () => ({ getTraining: vi.fn() }));
vi.mock("@/lib/api/uploads", () => ({ getPlaces: vi.fn().mockResolvedValue([]) }));
vi.mock("@/components/shared/noteDetail", () => ({ prefetchNoteDetail: vi.fn() }));
vi.mock("@/lib/api/client", async (importOriginal) => ({ ...(await importOriginal<object>()), refreshSession: vi.fn() }));

const ZERO = { total: 0, due_soon: 0 };
const QUIET: TodaySummary = {
  waiting: 0,
  due_soon: 0,
  lanes: { approve: ZERO, coder: ZERO, provider: ZERO, compliance: ZERO },
  provider_reasons: { questions: ZERO, waiting_on_provider: ZERO },
  next_up: [],
  batches: [],
};
const NOTHING_ASSIGNED = { sets: [], scores: { claim: { notes: 0 } } } as unknown as TrainingOverview;
const KEYS = ["today", "practice-setup", "team", "plan-status", "training", "places"];

function signIn(role: Role): void {
  setSession({ access_token: "token", user: { ...CODER, role } });
}

describe("TodayScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    KEYS.forEach(forgetRemote);
    vi.mocked(getToday).mockResolvedValue(QUIET);
    vi.mocked(getSetup).mockResolvedValue(setupWith());
    vi.mocked(getTeam).mockResolvedValue(teamOf(1));
    vi.mocked(getPlanStatus).mockResolvedValue(planStatus());
    vi.mocked(getTraining).mockResolvedValue(NOTHING_ASSIGNED);
    vi.mocked(saveChecks).mockResolvedValue(undefined);
    vi.mocked(saveSecurity).mockResolvedValue(undefined);
    vi.mocked(dismissFirstRun).mockResolvedValue(undefined);
    vi.mocked(refreshSession).mockResolvedValue(true);
  });

  afterEach(() => clearSession());

  it("gives a new admin the first steps in place of the review button, the first step as the one primary action", async () => {
    signIn("admin");
    render(<TodayScreen />);
    const checklist = await screen.findByRole("region", { name: "Get set up" });
    expect(within(checklist).getByText("0 of 6 done")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Start reviewing" })).not.toBeInTheDocument();
    const add = within(checklist).getByRole("link", { name: "Add provider" });
    expect(add).toHaveAttribute("href", "/settings/setup?section=providers&open=addProvider");
    expect(add).toHaveClass("bg-primary");
    expect(screen.getByRole("link", { name: "Upload notes" })).not.toHaveClass("bg-primary");
    expect(within(checklist).getByRole("link", { name: "Add your payers" })).toHaveAttribute("href", "/settings/setup?section=payers");
    expect(within(checklist).queryByRole("button", { name: "Hide" })).not.toBeInTheDocument();
  });

  it("saves the checks inline, applies the recommended security and hides the steps once providers are in", async () => {
    signIn("admin");
    vi.mocked(getSetup).mockResolvedValue(setupWith({ providers: true }));
    const user = userEvent.setup();
    render(<TodayScreen />);
    const checklist = await screen.findByRole("region", { name: "Get set up" });
    await user.click(within(checklist).getByRole("switch", { name: "Quality measures (MIPS)" }));
    await user.click(within(checklist).getByRole("button", { name: "Save checks" }));
    expect(saveChecks).toHaveBeenCalledWith({ em: true, icd: true, cdi: true, audit: true, mips: true, hcc: false });
    await user.click(within(checklist).getByRole("button", { name: "Use recommended" }));
    await waitFor(() => expect(saveSecurity).toHaveBeenCalledWith(RECOMMENDED_SECURITY));
    await waitFor(() => expect(refreshSession).toHaveBeenCalled());
    await user.click(within(checklist).getByRole("button", { name: "Hide" }));
    await waitFor(() => expect(dismissFirstRun).toHaveBeenCalled());
    expect(getSetup).toHaveBeenCalledTimes(4);
  });

  it("leaves the steps out once all are done and makes uploading the main action while there are no notes", async () => {
    signIn("admin");
    vi.mocked(getSetup).mockResolvedValue(setupWith({ providers: true, payer: true, checks: true, security: true }));
    vi.mocked(getTeam).mockResolvedValue(teamOf(3));
    vi.mocked(getPlanStatus).mockResolvedValue(planStatus({ standing: "active", plan: "professional" }));
    render(<TodayScreen />);
    await waitFor(() => expect(screen.getByRole("link", { name: "Upload notes" })).toHaveClass("bg-primary"));
    expect(screen.queryByRole("region", { name: "Get set up" })).not.toBeInTheDocument();
  });

  it("starts a coder on their own next note and never asks for the practice setup", async () => {
    signIn("coder");
    vi.mocked(getToday).mockResolvedValue({ ...QUIET, waiting: 1, next_up: [{ ...ROW, id: "note-7", assigned_to: CODER.id }] });
    render(<TodayScreen />);
    expect(await screen.findByRole("link", { name: "Start reviewing" })).toHaveAttribute("href", "/notes/note-7?lane=coder");
    expect(getSetup).not.toHaveBeenCalled();
  });

  it("starts CDI on the questions to send and billers on ready to bill", async () => {
    signIn("cdi");
    const { unmount } = render(<TodayScreen />);
    expect(await screen.findByRole("link", { name: "Send questions" })).toHaveAttribute("href", "/queue?lane=provider&reason=questions");
    unmount();
    forgetRemote("today");
    signIn("biller");
    render(<TodayScreen />);
    expect(await screen.findByRole("link", { name: "Start billing" })).toHaveAttribute("href", "/billing");
  });

  it("shows open assigned training so it is reachable without a sidebar entry", async () => {
    signIn("biller");
    vi.mocked(getTraining).mockResolvedValue({
      ...NOTHING_ASSIGNED,
      sets: [{ id: "set-1", purpose: "training", started_at: "2026-11-20T10:00:00+00:00", done: 2, total: 10 }],
    });
    render(<TodayScreen />);
    const card = await screen.findByRole("region", { name: "Assigned to you" });
    expect(within(card).getByRole("link", { name: /^Code Training set assigned/ })).toHaveAttribute("href", "/training/set-1");
    expect(within(card).getByRole("link", { name: "Training" })).toHaveAttribute("href", "/training");
  });
});
