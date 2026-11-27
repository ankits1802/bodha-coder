import { LegalBlockView } from "./LegalBlockView";
import type { LegalSection } from "./types";

export function LegalSectionView({ section, number }: { section: LegalSection; number: string | null }) {
  const headingId = section.id;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-4">
      <h2 id={headingId} className="m-0 scroll-mt-6 text-title3 font-semibold tracking-headline">
        {number ? <><span className="tabular-nums text-secondary">{number}</span>{" "}</> : null}
        {section.heading}
      </h2>
      {section.blocks.map((block, index) => (
        <LegalBlockView key={`${block.kind}-${index}`} block={block} />
      ))}
    </section>
  );
}
