import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { generateStaticParams } from "@/app/(marketing)/legal/[document]/page";
import { CATALOG } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { haptic } from "@/lib/haptics";
import { FOOTER_SECTIONS, NAV_SECTIONS, SECTION_IDS } from "../anchors";
import { LandingPage as Landing } from "../LandingPage";
import { PRICING_TEXT } from "../pricing/strings";
import { SAMPLE_TEXT } from "../sample/strings";
import { LANDING_TEXT } from "../strings";

vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

function LandingPage() {
  return <Landing catalog={CATALOG} />;
}

describe("LandingPage", () => {
  beforeEach(() => {
    vi.mocked(haptic).mockClear();
  });

  it("reads as one headline, the three acts and the figures", () => {
    render(<LandingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(LANDING_TEXT.hero.title);
    expect(screen.getByRole("heading", { level: 2, name: "Upload. Review. Defend." })).toBeInTheDocument();
    for (const act of LANDING_TEXT.story.acts) {
      expect(screen.getByRole("heading", { level: 3, name: act.title })).toBeInTheDocument();
    }
    expect(screen.getAllByText("100%")).toHaveLength(2);
    expect(screen.getByRole("heading", { level: 2, name: LANDING_TEXT.demo.title })).toBeInTheDocument();
  });

  it("starts a free trial from the nav, the hero, the sample note, the close and the footer, with a demo request beside each", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    const trials = screen.getAllByRole("link", { name: LANDING_TEXT.startTrial });
    expect(trials).toHaveLength(4);
    for (const link of trials) expect(link).toHaveAttribute("href", "/sign-up");
    expect(screen.getByRole("link", { name: LANDING_TEXT.nav.startFree })).toHaveAttribute("href", "/sign-up");
    const [heroDemo, ...otherDemos] = screen.getAllByRole("button", { name: LANDING_TEXT.requestDemo });
    expect(otherDemos).toHaveLength(2);
    if (!heroDemo) throw new Error("no demo request button");
    await user.click(heroDemo);
    expect(screen.getByRole("dialog", { name: LANDING_TEXT.form.title })).toBeInTheDocument();
  });

  it("turns the evidence off and back on with a haptic tick", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    const toggle = screen.getByRole("switch", { name: LANDING_TEXT.product.evidence });
    const scope = toggle.closest("[data-evidence]");
    await user.click(toggle);
    expect(scope).toHaveAttribute("data-evidence", "off");
    expect(toggle).toHaveAttribute("aria-checked", "false");
    await user.click(toggle);
    expect(scope).toHaveAttribute("data-evidence", "on");
    expect(vi.mocked(haptic).mock.calls).toEqual([["select"], ["select"]]);
  });

  it("approves the sample with a success haptic and undoes it", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    await user.click(screen.getByRole("button", { name: LANDING_TEXT.numbers.approve }));
    expect(screen.getByRole("button", { name: LANDING_TEXT.numbers.approved })).toHaveAttribute("aria-pressed", "true");
    expect(vi.mocked(haptic)).toHaveBeenLastCalledWith("success");
    await user.click(screen.getByRole("button", { name: LANDING_TEXT.numbers.approved }));
    expect(screen.getByRole("button", { name: LANDING_TEXT.numbers.approve })).toHaveAttribute("aria-pressed", "false");
  });

  it("links the nav and the footer to sections that exist on the page", () => {
    render(<LandingPage />);
    for (const key of new Set([...NAV_SECTIONS, ...FOOTER_SECTIONS])) {
      const links = screen.getAllByRole("link", { name: LANDING_TEXT.sections[key] });
      expect(links.length).toBeGreaterThan(0);
      for (const link of links) expect(link).toHaveAttribute("href", `#${SECTION_IDS[key]}`);
      expect(document.getElementById(SECTION_IDS[key])).not.toBeNull();
    }
  });

  it("links the footer to the legal documents, each a route that exists", () => {
    render(<LandingPage />);
    const legal = screen.getByRole("navigation", { name: "Legal" });
    const links = within(legal).getAllByRole("link");
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Terms", "/legal/terms"],
      ["Privacy", "/legal/privacy"],
      ["BAA", "/legal/baa"],
      ["Security overview", "/legal/security"],
      ["Subprocessors", "/legal/subprocessors"],
    ]);
    const routes = generateStaticParams().map(({ document }) => `/legal/${document}`);
    for (const link of links) expect(routes).toContain(link.getAttribute("href"));
  });

  it("opens the section menu and closes it with Escape, back on its button", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    const button = screen.getByRole("button", { name: LANDING_TEXT.nav.sections });
    const before = screen.getAllByRole("link", { name: LANDING_TEXT.sections.faq }).length;
    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("link", { name: LANDING_TEXT.sections.faq })).toHaveLength(before + 1);
    await user.keyboard("{Escape}");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveFocus();
  });

  it("gives every desk a tab, in order, and the sample note, estimator, workflow, pricing and questions their headings", () => {
    render(<LandingPage />);
    const desks = LANDING_TEXT.desks;
    const labels = within(screen.getByRole("tablist", { name: desks.tabsLabel }))
      .getAllByRole("tab")
      .map((tab) => tab.textContent);
    expect(labels).toEqual([desks.coders.tab, desks.cdi.tab, desks.compliance.tab, desks.billers.tab, desks.providers.tab, desks.admins.tab]);
    expect(within(screen.getByRole("tablist", { name: SAMPLE_TEXT.tabsLabel })).getAllByRole("tab")).toHaveLength(3);
    expect(screen.getByRole("heading", { level: 3, name: desks.coders.title })).toBeInTheDocument();
    const titles = [SAMPLE_TEXT.title, desks.title, LANDING_TEXT.bento.title, LANDING_TEXT.worth.title, LANDING_TEXT.flow.title, PRICING_TEXT.teaser.title.join(" ")];
    for (const title of [...titles, LANDING_TEXT.faq.title]) {
      expect(screen.getByRole("heading", { level: 2, name: title })).toBeInTheDocument();
    }
    expect(screen.getAllByRole("heading", { level: 3, name: /./ }).length).toBeGreaterThan(20);
  });
});
