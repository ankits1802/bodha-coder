export const SECTION_IDS = {
  how: "how",
  teams: "teams",
  features: "features",
  worth: "worth",
  flow: "flow",
  security: "security",
  faq: "faq",
  demo: "demo",
} as const;

export type SectionKey = keyof typeof SECTION_IDS;
export type LinkedSection = Exclude<SectionKey, "demo">;

export const NAV_SECTIONS: readonly LinkedSection[] = ["how", "teams", "features", "security", "faq"];
export const FOOTER_SECTIONS: readonly LinkedSection[] = ["how", "teams", "features", "worth", "flow", "security", "faq"];

export function sectionHref(key: SectionKey): string {
  return `#${SECTION_IDS[key]}`;
}
