import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LegalDocumentPage, { generateMetadata, generateStaticParams } from "@/app/(marketing)/legal/[document]/page";
import LegalIndexPage from "@/app/(marketing)/legal/page";
import { LEGAL_SLUGS, type LegalSlug } from "@/components/shared/legal/legalLinks";
import { LEGAL_DRAFT } from "../config";
import { LEGAL_DOCUMENTS } from "../documents";
import { LegalDocument } from "../LegalDocument";

const EXPECTED_TITLES: Record<LegalSlug, string> = {
  terms: "Terms of Service",
  privacy: "Privacy Policy",
  baa: "Business Associate Agreement",
  "acceptable-use": "Acceptable Use Policy",
  subprocessors: "Subprocessors",
  security: "Security Overview",
};

function pageFor(document: string) {
  return LegalDocumentPage({ params: Promise.resolve({ document }) });
}

describe("legal routes", () => {
  it("prerenders one route per legal document", () => {
    expect(generateStaticParams()).toEqual([
      { document: "terms" },
      { document: "privacy" },
      { document: "baa" },
      { document: "acceptable-use" },
      { document: "subprocessors" },
      { document: "security" },
    ]);
  });

  it.each(LEGAL_SLUGS)("renders the %s route with its title as the only level 1 heading", async (slug) => {
    render(await pageFor(slug));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(EXPECTED_TITLES[slug]);
    const metadata = await generateMetadata({ params: Promise.resolve({ document: slug }) });
    expect(metadata.title).toBe(EXPECTED_TITLES[slug]);
  });

  it("answers an unknown document with not found", async () => {
    await expect(pageFor("cookies")).rejects.toThrow();
    expect(await generateMetadata({ params: Promise.resolve({ document: "cookies" }) })).toEqual({});
  });

  it("lists every document on the legal index", () => {
    render(<LegalIndexPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Legal");
    for (const slug of LEGAL_SLUGS) {
      expect(screen.getByRole("link", { name: new RegExp(EXPECTED_TITLES[slug]) })).toHaveAttribute("href", `/legal/${slug}`);
    }
  });
});

describe("draft label", () => {
  it("shows Draft for review only while the document is a draft", () => {
    const { rerender } = render(<LegalDocument document={LEGAL_DOCUMENTS.terms} draft />);
    expect(screen.getByText("Draft for review")).toBeInTheDocument();
    rerender(<LegalDocument document={LEGAL_DOCUMENTS.terms} draft={false} />);
    expect(screen.queryByText("Draft for review")).not.toBeInTheDocument();
  });

  it.each(LEGAL_SLUGS)("follows the LEGAL_DRAFT flag on the %s route", async (slug) => {
    render(await pageFor(slug));
    expect(screen.queryAllByText("Draft for review")).toHaveLength(LEGAL_DRAFT ? 1 : 0);
  });

  it("follows the LEGAL_DRAFT flag on the index and keeps drafts out of search results", async () => {
    render(<LegalIndexPage />);
    expect(screen.queryAllByText("Draft for review")).toHaveLength(LEGAL_DRAFT ? 1 : 0);
    const metadata = await generateMetadata({ params: Promise.resolve({ document: "terms" }) });
    expect(metadata.robots).toEqual({ index: !LEGAL_DRAFT, follow: true });
  });
});

describe("table of contents", () => {
  it.each(LEGAL_SLUGS)("links every section of %s to a level 2 heading with the same id", (slug) => {
    const document = LEGAL_DOCUMENTS[slug];
    render(<LegalDocument document={document} draft={false} />);
    const contents = screen.getByRole("navigation", { name: "Contents" });
    const anchors = within(contents).getAllByRole("link");
    expect(anchors).toHaveLength(document.sections.length);
    anchors.forEach((anchor, index) => {
      const section = document.sections[index];
      if (!section) throw new Error(`no section ${index} in ${slug}`);
      expect(anchor).toHaveAttribute("href", `#${section.id}`);
      const target = window.document.getElementById(section.id);
      expect(target?.tagName).toBe("H2");
      expect(target).toHaveTextContent(section.heading);
      expect(anchor).toHaveTextContent(section.heading);
    });
  });

  it("numbers the sections of the agreements and not of the reference pages", () => {
    const { unmount } = render(<LegalDocument document={LEGAL_DOCUMENTS.baa} draft={false} />);
    expect(screen.getByRole("heading", { level: 2, name: "1. Agreement and effective date" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "1. Agreement and effective date" })).toHaveAttribute("href", "#agreement");
    unmount();
    render(<LegalDocument document={LEGAL_DOCUMENTS.security} draft={false} />);
    expect(screen.getByRole("heading", { level: 2, name: "Hosting and encryption" })).toBeInTheDocument();
  });
});
