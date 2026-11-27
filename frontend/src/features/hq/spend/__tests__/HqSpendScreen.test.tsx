import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getHqExpenditure } from "@/lib/api/hq";
import { saveFile } from "@/lib/download";
import { HqSpendScreen } from "../HqSpendScreen";
import { NOVEMBER_SPEND, NO_SPEND, WITH_QUIET_PRACTICE } from "./spendFixtures";

const navigation = vi.hoisted(() => ({ search: "", replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/hq/spend",
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));
vi.mock("@/lib/api/hq", () => ({ getHqExpenditure: vi.fn() }));
vi.mock("@/lib/download", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/download")>()),
  saveFile: vi.fn(),
}));

function readText(blob: Blob): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.readAsText(blob);
  });
}

function rowOf(name: string): HTMLElement {
  const row = screen.getByText(name).closest("tr");
  if (!row) throw new Error(`no row for ${name}`);
  return row;
}

describe("HqSpendScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-28T12:00:00Z"));
    navigation.search = "";
    vi.mocked(getHqExpenditure).mockResolvedValue(NOVEMBER_SPEND);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("asks for this month by default and shows the totals", async () => {
    render(<HqSpendScreen />);
    const totals = await screen.findByRole("region", { name: "Spend in range" });
    expect(getHqExpenditure).toHaveBeenCalledWith({ from: "2026-11-01", to: "2026-11-28" });
    expect(within(totals).getByText("$2.14")).toBeInTheDocument();
    expect(within(totals).getByText("1 without a price · gemini-unlisted")).toBeInTheDocument();
    expect(within(totals).getByText("3,350,000")).toBeInTheDocument();
    expect(screen.getByText("1 Nov 2026 – 28 Nov 2026 · UTC")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "This month" })).toHaveAttribute("aria-checked", "true");
  });

  it("lists practices and opens each one to its providers", async () => {
    const user = userEvent.setup();
    render(<HqSpendScreen />);
    const lakeside = await screen.findByRole("button", { name: "Lakeside" });
    expect(within(rowOf("Lakeside")).getByText("$1.14")).toBeInTheDocument();
    expect(within(rowOf("Lakeside")).getByText("$249 / provider / month")).toBeInTheDocument();
    expect(screen.queryByText("Elena Varga")).not.toBeInTheDocument();
    await user.click(lakeside);
    expect(lakeside).toHaveAttribute("aria-expanded", "true");
    expect(within(rowOf("Elena Varga")).getAllByText("$1.06")).toHaveLength(2);
    expect(within(rowOf("Omar Haddad")).getByText("$0.08")).toBeInTheDocument();
    expect(within(rowOf("Omar Haddad")).getByText("—")).toBeInTheDocument();
    expect(screen.queryByText("Ana Ruiz")).not.toBeInTheDocument();
  });

  it("lists a practice with no model use at zero, with nothing to open", async () => {
    vi.mocked(getHqExpenditure).mockResolvedValue(WITH_QUIET_PRACTICE);
    render(<HqSpendScreen />);
    await screen.findByRole("button", { name: "Lakeside" });
    expect(within(rowOf("Quiet Creek")).getByText("$0.00")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Quiet Creek" })).not.toBeInTheDocument();
  });

  it("puts a preset's days in the address", async () => {
    navigation.search = "from=2026-11-03&to=2026-11-20";
    const user = userEvent.setup();
    render(<HqSpendScreen />);
    await screen.findByRole("region", { name: "Spend in range" });
    expect(getHqExpenditure).toHaveBeenCalledWith({ from: "2026-11-03", to: "2026-11-20" });
    expect(screen.getByRole("radio", { name: "This month" })).toHaveAttribute("aria-checked", "false");
    await user.click(screen.getByRole("radio", { name: "Last month" }));
    expect(navigation.replace).toHaveBeenCalledWith("/hq/spend?from=2026-10-01&to=2026-10-31", { scroll: false });
    await user.click(screen.getByRole("radio", { name: "This year" }));
    expect(navigation.replace).toHaveBeenLastCalledWith("/hq/spend?from=2026-01-01&to=2026-11-28", { scroll: false });
  });

  it("downloads the provider rows as CSV", async () => {
    const user = userEvent.setup();
    render(<HqSpendScreen />);
    await screen.findByRole("region", { name: "Spend in range" });
    await user.click(screen.getByRole("button", { name: "Download CSV" }));
    await waitFor(() => expect(saveFile).toHaveBeenCalledTimes(1));
    const [blob, fileName] = vi.mocked(saveFile).mock.calls[0] ?? [];
    expect(fileName).toBe("bodha-spend-20261101-20261128.csv");
    expect(blob).toBeInstanceOf(Blob);
    expect((blob as Blob).type).toBe("text/csv");
    const lines = (await readText(blob as Blob)).split("\n");
    expect(lines).toHaveLength(4);
    expect(lines[1]).toBe("Lakeside,Elena Varga,3,1,1220000,150000,1.06,1.0600,0");
  });

  it("says when nothing was spent and offers no download", async () => {
    vi.mocked(getHqExpenditure).mockResolvedValue(NO_SPEND);
    render(<HqSpendScreen />);
    expect(await screen.findByText("No model use in this range")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download CSV" })).toBeDisabled();
  });
});
