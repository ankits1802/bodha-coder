import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getHqActivity, getHqExpenditure, getHqPracticePage, getHqPracticePeople } from "@/lib/api/hq";
import { HqPracticeScreen } from "../HqPracticeScreen";
import { ACTIVITY, PAGE, PEOPLE, QUIET_SPEND } from "./practiceFixtures";

const navigation = vi.hoisted(() => ({ search: "", replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/hq/practices/p1",
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));
vi.mock("@/lib/api/hq", () => ({
  getHqPracticePage: vi.fn(),
  getHqPracticePeople: vi.fn(),
  getHqExpenditure: vi.fn(),
  getHqActivity: vi.fn(),
  renewPractice: vi.fn(),
  appointAdmin: vi.fn(),
}));

function rowOf(text: string): HTMLElement {
  const row = screen.getByText(text).closest("tr");
  if (!row) throw new Error(`no row for ${text}`);
  return row;
}

describe("HqPracticeScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-28T12:00:00Z"));
    navigation.search = "";
    vi.mocked(getHqPracticePage).mockResolvedValue(PAGE);
    vi.mocked(getHqPracticePeople).mockResolvedValue(PEOPLE);
    vi.mocked(getHqExpenditure).mockResolvedValue(QUIET_SPEND);
    vi.mocked(getHqActivity).mockResolvedValue(ACTIVITY);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("opens on the people of the practice with role, status and two-step", async () => {
    render(<HqPracticeScreen practiceId="p1" />);
    expect(await screen.findByRole("heading", { name: "Lakeside Primary Care" })).toBeInTheDocument();
    expect(await screen.findByText("Tomas Reyes")).toBeInTheDocument();
    expect(getHqPracticePeople).toHaveBeenCalledWith("p1");
    expect(screen.getByRole("radio", { name: "People" })).toHaveAttribute("aria-checked", "true");
    expect(within(rowOf("Tomas Reyes")).getByText("Coder")).toBeInTheDocument();
    expect(within(rowOf("Tomas Reyes")).getByText("Invited")).toBeInTheDocument();
    expect(within(rowOf("priya@lakeside.example.com")).getByText("Admin")).toBeInTheDocument();
    expect(within(rowOf("priya@lakeside.example.com")).getByText("On")).toBeInTheDocument();
  });

  it("offers no renewal or new admin for a closed practice", async () => {
    vi.mocked(getHqPracticePage).mockResolvedValue({ ...PAGE, practice: { ...PAGE.practice, status: "closed", closed_at: "2026-11-27T10:00:00Z" } });
    render(<HqPracticeScreen practiceId="p1" />);
    expect(await screen.findByRole("heading", { name: "Lakeside Primary Care" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Renew" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add admin" })).not.toBeInTheDocument();
  });

  it("keeps the chosen tab in the address", async () => {
    const user = userEvent.setup();
    render(<HqPracticeScreen practiceId="p1" />);
    await screen.findByText("Tomas Reyes");
    await user.click(screen.getByRole("radio", { name: "Places" }));
    expect(navigation.replace).toHaveBeenCalledWith("/hq/practices/p1?tab=places", { scroll: false });
  });

  it("lists the places the practice uses", async () => {
    navigation.search = "tab=places";
    render(<HqPracticeScreen practiceId="p1" />);
    expect(await screen.findByText("Skilled nursing facility")).toBeInTheDocument();
    expect(within(rowOf("Office")).getByText("40")).toBeInTheDocument();
    expect(within(rowOf("Office")).getByText("Active")).toBeInTheDocument();
    expect(within(rowOf("Skilled nursing facility")).getByText("Off")).toBeInTheDocument();
  });

  it("shows the plan and renewal facts and opens the renewal from the header", async () => {
    navigation.search = "tab=plan";
    const user = userEvent.setup();
    render(<HqPracticeScreen practiceId="p1" />);
    expect(await screen.findByText("Paying · Stripe")).toBeInTheDocument();
    expect(screen.getByText("2 of 10 seats")).toBeInTheDocument();
    expect(screen.getByText("Renews 1 Mar 2099")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Renew" }));
    expect(screen.getByRole("radio", { name: "1 year" })).toBeChecked();
  });

  it("links a practice to its organization and says how it is billed", async () => {
    navigation.search = "tab=plan";
    const grouped = { ...PAGE.practice, organization_id: "o1", organization_name: "Acme Health", combined_billing: true };
    vi.mocked(getHqPracticePage).mockResolvedValue({ ...PAGE, practice: grouped });
    render(<HqPracticeScreen practiceId="p1" />);
    expect(await screen.findByRole("link", { name: "Acme Health" })).toHaveAttribute("href", "/hq/organizations/o1");
    expect(screen.getByText("Billed through the organization")).toBeInTheDocument();
  });

  it("shows a practice with no model use at zero instead of hiding it", async () => {
    navigation.search = "tab=spend";
    render(<HqPracticeScreen practiceId="p1" />);
    const row = await screen.findByText("Lakeside Primary Care", { selector: "td span" });
    expect(getHqExpenditure).toHaveBeenCalledWith({ from: "2026-11-01", to: "2026-11-28" }, { practice_id: "p1" });
    expect(within(row.closest("tr") as HTMLElement).getAllByText("$0.00").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Lakeside Primary Care" })).not.toBeInTheDocument();
  });

  it("filters HQ activity to the practice", async () => {
    navigation.search = "tab=activity";
    render(<HqPracticeScreen practiceId="p1" />);
    expect(await screen.findByText("Practice renewed")).toBeInTheDocument();
    expect(getHqActivity).toHaveBeenCalledWith({ practice_id: "p1", action: null, offset: 0 });
  });
});
