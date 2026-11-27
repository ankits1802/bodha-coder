import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HelpScreen } from "@/features/help/HelpScreen";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { getTours, saveTour } from "@/lib/api/tours";
import type { TourRecord } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { closeOverlay } from "../../overlays";
import { TourHost } from "../TourHost";
import { TOUR_VERSION } from "../tourSteps";
import { TOURS_KEY } from "../useTourRecords";

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation, usePathname: () => window.location.pathname }));
vi.mock("@/lib/api/tours", () => ({ getTours: vi.fn(), saveTour: vi.fn() }));

const SEEN: TourRecord = { tour: "practice", version: TOUR_VERSION, completed_at: "2026-11-28T10:00:00+00:00", skipped_at: null };
const CODER_STEPS = 10;

function searchButtonWith(reducedMotion: boolean): Element["scrollIntoView"] {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: reducedMotion && query === "(prefers-reduced-motion: reduce)", media: query }));
  const button = document.createElement("button");
  button.dataset.tour = "search";
  button.getBoundingClientRect = () => ({ top: 100, left: 10, width: 200, height: 32, right: 210, bottom: 132, x: 10, y: 100, toJSON: () => ({}) });
  button.scrollIntoView = vi.fn<Element["scrollIntoView"]>();
  document.body.append(button);
  return button.scrollIntoView;
}

async function openFirstTour(onMenu = vi.fn()) {
  vi.mocked(getTours).mockResolvedValue([]);
  render(<TourHost user={CODER} onMenu={onMenu} />);
  return screen.findByRole("dialog", { name: "Welcome to Bodha Assure" });
}

describe("TourHost", () => {
  beforeEach(() => {
    forgetRemote(TOURS_KEY);
    closeOverlay();
    window.history.replaceState(null, "", "/today");
    navigation.push.mockReset().mockImplementation((path: string) => window.history.pushState(null, "", path));
    vi.mocked(getTours).mockReset();
    vi.mocked(saveTour).mockReset().mockResolvedValue(SEEN);
  });

  afterEach(() => {
    clearSession();
    vi.unstubAllGlobals();
    document.querySelectorAll("[data-tour]").forEach((node) => node.remove());
  });

  it("opens the first time, opens the menu on a narrow screen and records a skip", async () => {
    const onMenu = vi.fn();
    const dialog = await openFirstTour(onMenu);
    expect(dialog).toHaveTextContent(`1 of ${CODER_STEPS}`);
    expect(onMenu).toHaveBeenCalledWith(true);
    await userEvent.setup().click(screen.getByRole("button", { name: "Skip tour" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(saveTour).toHaveBeenCalledWith("practice", { version: TOUR_VERSION, outcome: "skipped" });
    expect(onMenu).toHaveBeenLastCalledWith(false);
  });

  it("stays closed once this version of the tour is recorded", async () => {
    vi.mocked(getTours).mockResolvedValue([SEEN]);
    render(<TourHost user={CODER} onMenu={vi.fn()} />);
    await waitFor(() => expect(getTours).toHaveBeenCalled());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("never opens for a billing-only account", () => {
    render(<TourHost user={{ ...CODER, role: "admin", billing_only: true }} onMenu={vi.fn()} />);
    expect(getTours).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("moves with the arrow keys and Enter, keeps focus in the card and skips with Escape", async () => {
    const dialog = await openFirstTour();
    const user = userEvent.setup();
    expect(screen.getByRole("button", { name: "Next" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(dialog).toHaveAccessibleName("Search");
    expect(dialog).toHaveTextContent(`2 of ${CODER_STEPS}`);
    await user.keyboard("{ArrowLeft}");
    expect(dialog).toHaveAccessibleName("Welcome to Bodha Assure");
    await user.keyboard("{Enter}");
    expect(dialog).toHaveAccessibleName("Search");
    await user.tab();
    expect(screen.getByRole("button", { name: "Skip tour" })).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Next" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(saveTour).toHaveBeenCalledWith("practice", { version: TOUR_VERSION, outcome: "skipped" });
  });

  it("opens each area's page, records completion and returns to the starting page", async () => {
    await openFirstTour();
    const user = userEvent.setup();
    for (let step = 1; step < CODER_STEPS; step += 1) await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Your account");
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(saveTour).toHaveBeenCalledWith("practice", { version: TOUR_VERSION, outcome: "completed" });
    expect(navigation.push.mock.calls.map(([path]) => path)).toEqual(["/upload", "/queue", "/help", "/today"]);
  });

  it("replays from Help without recording the tour again", async () => {
    vi.mocked(getTours).mockResolvedValue([SEEN]);
    setSession({ access_token: "token", user: CODER });
    render(
      <>
        <HelpScreen />
        <TourHost user={CODER} onMenu={vi.fn()} />
      </>,
    );
    await waitFor(() => expect(getTours).toHaveBeenCalled());
    const user = userEvent.setup();
    const replay = screen.getByRole("button", { name: "Take the tour" });
    await user.click(replay);
    expect(await screen.findByRole("dialog", { name: "Welcome to Bodha Assure" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Skip tour" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(saveTour).not.toHaveBeenCalled();
    expect(replay).toHaveFocus();
  });

  it("highlights the real element, announces it and scrolls without animation for reduced motion", async () => {
    const scroll = searchButtonWith(true);
    await openFirstTour();
    await userEvent.setup().keyboard("{ArrowRight}");
    expect(await screen.findByText(`2 of ${CODER_STEPS}. Search, highlighted. Find any note by patient, provider, file or code.`)).toBeInTheDocument();
    expect(scroll).toHaveBeenCalledWith({ block: "nearest", inline: "nearest", behavior: "auto" });
    expect(document.querySelector("[data-spotlight='target']")).toBeInTheDocument();
    expect(document.querySelector("[data-side]")).toHaveAttribute("data-side", "right");
  });

  it("scrolls smoothly when motion is welcome", async () => {
    const scroll = searchButtonWith(false);
    await openFirstTour();
    await userEvent.setup().keyboard("{ArrowRight}");
    await waitFor(() => expect(scroll).toHaveBeenCalledWith({ block: "nearest", inline: "nearest", behavior: "smooth" }));
  });
});
