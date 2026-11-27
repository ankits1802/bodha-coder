export const LEGAL_SLUGS = ["terms", "privacy", "baa", "acceptable-use", "subprocessors", "security"] as const;

export type LegalSlug = (typeof LEGAL_SLUGS)[number];

export const LEGAL_INDEX_PATH = "/legal";

export function legalPath(slug: LegalSlug): string {
  return `${LEGAL_INDEX_PATH}/${slug}`;
}

export const LEGAL_LINK_TEXT = {
  heading: "Legal",
  links: {
    terms: "Terms",
    privacy: "Privacy",
    baa: "BAA",
    "acceptable-use": "Acceptable use",
    subprocessors: "Subprocessors",
    security: "Security overview",
  },
} as const satisfies { heading: string; links: Record<LegalSlug, string> };

export const FOOTER_LEGAL_SLUGS: readonly LegalSlug[] = ["terms", "privacy", "baa", "security", "subprocessors"];
