import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getHqPlaces, getHqPractices } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { LAKESIDE } from "../../practice/__tests__/practiceFixtures";
import { HqPracticesScreen } from "../HqPracticesScreen";
import { countPractices, inPracticeFilter, practicesPath } from "../practiceFilters";

const navigation = vi.hoisted(() => ({ search: "" }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/hq/practices",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/api/hq", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/hq")>()),
  getHqPractices: vi.fn(),
  getHqPlaces: vi.fn(),
}));

const TRIAL: HqPractice = { ...LAKESIDE, id: "p2", name: "Harbor Pediatrics", status: "trial" };
const BLOCKED: HqPractice = { ...LAKESIDE, id: "p3", name: "Bay Family Medicine", status: "blocked" };
const ENDED: HqPractice = { ...LAKESIDE, id: "p4", name: "Cedar Clinic", status: "ended" };
const CLOSED: HqPractice = { ...LAKESIDE, id: "p5", name: "Dune Health", status: "closed" };
const ALL = [LAKESIDE, TRIAL, BLOCKED, ENDED, CLOSED];

describe("live practices", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    navigation.search = "";
    vi.mocked(getHqPractices).mockResolvedValue(ALL);
    vi.mocked(getHqPlaces).mockResolvedValue([]);
  });

  it("are the practices on trial or active, as the overview counts them", () => {
    expect(ALL.filter((practice) => inPracticeFilter(practice, "live")).map((practice) => practice.name)).toEqual([
      "Lakeside Primary Care",
      "Harbor Pediatrics",
    ]);
    expect(countPractices(ALL, "live")).toBe(2);
  });

  it("have their own address, and every practice the plain list", () => {
    expect(practicesPath("live")).toBe("/hq/practices?status=live");
    expect(practicesPath("trial")).toBe("/hq/practices?status=trial");
    expect(practicesPath("all")).toBe("/hq/practices");
  });

  it("open from the address with the Live filter chosen", async () => {
    navigation.search = "status=live";
    render(<HqPracticesScreen />);
    expect(await screen.findByRole("link", { name: "Lakeside Primary Care" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Harbor Pediatrics" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Bay Family Medicine" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dune Health" })).not.toBeInTheDocument();
    const live = screen.getByRole("radio", { name: /^Live/ });
    expect(live).toHaveAttribute("aria-checked", "true");
    expect(live).toHaveTextContent("2");
  });
});
