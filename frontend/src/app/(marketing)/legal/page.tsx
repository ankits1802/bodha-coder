import type { Metadata } from "next";
import { LEGAL_INDEX_PATH } from "@/components/shared/legal/legalLinks";
import { LEGAL_DRAFT } from "@/features/legal/config";
import { LegalIndex } from "@/features/legal/LegalIndex";
import { legalRobots } from "@/features/legal/metadata";
import { LEGAL_TEXT } from "@/features/legal/strings";

export const metadata: Metadata = {
  title: LEGAL_TEXT.legal,
  description: LEGAL_TEXT.indexSummary,
  alternates: { canonical: LEGAL_INDEX_PATH },
  robots: legalRobots(LEGAL_DRAFT),
};

export default function LegalIndexPage() {
  return <LegalIndex draft={LEGAL_DRAFT} />;
}
