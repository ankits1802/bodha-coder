import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EmMix, EmMixLevel } from "@/lib/api/types";
import { EmMixView } from "../EmMixView";

function level(code: string, count: number, share: number, benchmark: number | null, points: number | null): EmMixLevel {
  const direction = points !== null && Math.abs(points) > 15 ? (points > 0 ? "above" : "below") : null;
  return { code, count, share, benchmark, points, direction };
}

const MIX: EmMix = {
  start: "2026-10-29",
  end: "2026-11-27",
  benchmark: { dataset: "CMS Evaluation and Management (E/M) Codes by Specialty", year: "2025", source_url: "https://www.cms.gov/example" },
  providers: [
    {
      id: "p1",
      name: "Elena Varga",
      specialty: "Internal medicine",
      cms_specialty: "INTERNAL MEDICINE",
      visits: 40,
      families: [
        {
          family: "office_established",
          label: "Office visit, established patient",
          visits: 40,
          has_benchmark: true,
          levels: [
            level("99211", 0, 0, 0, 0),
            level("99212", 0, 0, 0.05, -5),
            level("99213", 5, 0.125, 0.3, -17.5),
            level("99214", 20, 0.5, 0.55, -5),
            level("99215", 15, 0.375, 0.1, 27.5),
          ],
          chi_square: 8.901,
          degrees_of_freedom: 1,
          p_value: 0.00285,
          outlier: true,
          reasons: ["points", "chi_square"],
          lean: "higher",
        },
      ],
    },
    {
      id: "p2",
      name: "Omar Haddad",
      specialty: "Aerospace medicine",
      cms_specialty: null,
      visits: 1,
      families: [
        {
          family: "office_established",
          label: "Office visit, established patient",
          visits: 1,
          has_benchmark: false,
          levels: [level("99213", 1, 1, null, null)],
          chi_square: null,
          degrees_of_freedom: null,
          p_value: null,
          outlier: false,
          reasons: [],
          lean: null,
        },
      ],
    },
  ],
};

describe("EmMixView", () => {
  it("shows the legend once and each level's share beside the CMS share in text", () => {
    render(<EmMixView mix={MIX} />);

    const legend = within(screen.getByRole("list", { name: "Legend" })).getAllByRole("listitem");
    expect(legend.map((item) => item.textContent)).toEqual(["This provider", "CMS 2025"]);
    const varga = screen.getByRole("region", { name: "Elena Varga" });
    expect(varga).toHaveTextContent("40 visits");
    expect(varga).toHaveTextContent("Internal medicine · CMS INTERNAL MEDICINE");
    expect(within(varga).getByText("Higher levels than CMS")).toBeInTheDocument();
    expect(within(varga).getByText("37.5% · CMS 10%")).toBeInTheDocument();
    expect(within(varga).getByText("+27.5 pts")).toBeInTheDocument();
    expect(within(varga).getByText("12.5% · CMS 30%")).toBeInTheDocument();
    expect(within(varga).getByText("-17.5 pts")).toBeInTheDocument();
    expect(within(varga).getByText("χ² 8.901, df 1, p 0.003")).toBeInTheDocument();
  });

  it("says so when a provider's specialty has no CMS benchmark", () => {
    render(<EmMixView mix={MIX} />);

    const haddad = screen.getByRole("region", { name: "Omar Haddad" });
    expect(within(haddad).getByText("No CMS specialty match")).toBeInTheDocument();
    expect(within(haddad).getByText("No CMS data")).toBeInTheDocument();
    expect(within(haddad).getByText("100% · CMS —")).toBeInTheDocument();
    expect(within(haddad).queryByText(/pts$/)).not.toBeInTheDocument();
  });
});
