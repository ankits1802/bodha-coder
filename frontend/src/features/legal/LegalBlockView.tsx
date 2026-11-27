import Link from "next/link";
import { legalPath, type LegalSlug } from "@/components/shared/legal/legalLinks";
import { LEGAL_TITLES } from "./content/headings";
import { LegalTableView } from "./LegalTableView";
import { LegalText } from "./LegalText";
import { LEGAL_TEXT } from "./strings";
import type { LegalBlock } from "./types";

const LINK = "font-medium text-label underline decoration-separator decoration-1 underline-offset-4 hover:decoration-label";

function RelatedDocuments({ slugs }: { slugs: readonly LegalSlug[] }) {
  return (
    <nav aria-label={LEGAL_TEXT.related} className="rounded-panel bg-muted-panel px-5 py-4 print:hidden">
      <p className="m-0 text-subhead font-semibold text-secondary">{LEGAL_TEXT.related}</p>
      <ul className="mt-2 mb-0 flex list-none flex-wrap gap-x-6 gap-y-2 p-0 text-body">
        {slugs.map((slug) => (
          <li key={slug}>
            <Link href={legalPath(slug)} className={LINK}>
              {LEGAL_TITLES[slug]}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function LegalBlockView({ block }: { block: LegalBlock }) {
  switch (block.kind) {
    case "paragraph":
      return (
        <p className="m-0">
          <LegalText text={block.text} />
        </p>
      );
    case "notice":
      return (
        <p className="m-0 font-semibold">
          <LegalText text={block.text} />
        </p>
      );
    case "subheading":
      return <h3 className="mt-2 mb-0 text-headline font-semibold tracking-headline">{block.text}</h3>;
    case "bullets":
      return (
        <ul className="m-0 flex list-disc flex-col gap-2 pl-6 marker:text-secondary">
          {block.items.map((item) => (
            <li key={item} className="pl-1">
              <LegalText text={item} />
            </li>
          ))}
        </ul>
      );
    case "clauses":
      return (
        <ul className="m-0 flex list-none flex-col gap-3.5 p-0">
          {block.items.map((item) => (
            <li key={item.term}>
              <strong className="font-semibold">{item.term}</strong> <LegalText text={item.text} />
            </li>
          ))}
        </ul>
      );
    case "table":
      return <LegalTableView table={block.table} />;
    case "links":
      return <RelatedDocuments slugs={block.slugs} />;
  }
}
